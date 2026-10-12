import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Float, JSON
from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Application(Base):
    """
    One row per "job application" run: the CV + JD that were submitted,
    plus the full agent output (match report, tailored CV, cover letter,
    interview prep) so results can be revisited later.
    """
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=gen_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)

    cv_filename = Column(String, nullable=True)
    cv_raw_text = Column(Text, nullable=False)
    job_title = Column(String, nullable=True)
    job_description_text = Column(Text, nullable=False)

    match_score = Column(Float, default=0.0)
    skill_matches = Column(JSON, default=list)      # list[dict]
    skill_gaps = Column(JSON, default=list)          # list[str]

    tailored_cv_sections = Column(JSON, default=dict)
    cover_letter = Column(Text, nullable=True)
    interview_questions = Column(JSON, default=list)  # list[dict]

    status = Column(String, default="pending")  # pending|processing|complete|failed
    error_message = Column(Text, nullable=True)
