from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application
from app.schemas import ApplicationCreateResponse, ApplicationResultResponse
from app.parsers.document_parser import parse_cv, parse_job_description, UnsupportedFileType
from app.agents.graph import run_pipeline
from app.config import get_settings

logger = logging.getLogger("app.application")
router = APIRouter(prefix="/api/applications", tags=["applications"])


def _process_application(application_id: str) -> None:
    """Runs in a background task: executes the LangGraph pipeline and
    persists results (or the error) back onto the Application row."""
    from app.database import SessionLocal

    db: Session = SessionLocal()
    try:
        app_row: Application | None = (
            db.query(Application).filter(Application.id == application_id).first()
        )
        if app_row is None:
            return

        app_row.status = "processing"
        db.commit()

        cv_chunks = parse_cv_chunks_from_text(app_row.cv_raw_text)

        final_state = run_pipeline(
            cv_text=app_row.cv_raw_text,
            cv_chunks=cv_chunks,
            job_title=app_row.job_title or "",
            job_description=app_row.job_description_text,
        )

        app_row.match_score = final_state.get("match_score", 0.0)
        app_row.skill_matches = final_state.get("skill_matches", [])
        app_row.skill_gaps = final_state.get("skill_gaps", [])
        app_row.tailored_cv_sections = final_state.get("tailored_cv_sections", {})
        app_row.cover_letter = final_state.get("cover_letter", "")
        app_row.interview_questions = final_state.get("interview_questions", [])
        app_row.status = "complete"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for application %s", application_id)
        db.rollback()
        app_row = db.query(Application).filter(Application.id == application_id).first()
        if app_row is not None:
            app_row.status = "failed"
            app_row.error_message = str(exc)
            db.commit()
    finally:
        db.close()


def parse_cv_chunks_from_text(cv_text: str) -> list[str]:
    from app.parsers.document_parser import chunk_cv

    return chunk_cv(cv_text)


@router.post("", response_model=ApplicationCreateResponse)
async def create_application(
    background_tasks: BackgroundTasks,
    cv_file: UploadFile = File(...),
    job_title: str = Form(""),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    file_bytes = await cv_file.read()
    if len(file_bytes) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"CV file exceeds {settings.max_upload_mb}MB limit.")

    try:
        parsed_cv = parse_cv(cv_file.filename or "cv.txt", file_bytes)
    except UnsupportedFileType as exc:
        raise HTTPException(400, str(exc)) from exc

    if not parsed_cv.raw_text.strip():
        raise HTTPException(400, "Could not extract any text from the uploaded CV.")

    parsed_jd = parse_job_description(job_description)
    if not parsed_jd.raw_text.strip():
        raise HTTPException(400, "Job description text is empty.")

    application = Application(
        cv_filename=cv_file.filename,
        cv_raw_text=parsed_cv.raw_text,
        job_title=job_title or None,
        job_description_text=parsed_jd.raw_text,
        status="pending",
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    background_tasks.add_task(_process_application, application.id)

    return ApplicationCreateResponse(id=application.id, status=application.status)


@router.get("/{application_id}", response_model=ApplicationResultResponse)
def get_application(application_id: str, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(404, "Application not found.")
    return application


@router.get("", response_model=list[ApplicationResultResponse])
def list_applications(db: Session = Depends(get_db), limit: int = 20):
    applications = (
        db.query(Application)
        .order_by(Application.created_at.desc())
        .limit(limit)
        .all()
    )
    return applications
