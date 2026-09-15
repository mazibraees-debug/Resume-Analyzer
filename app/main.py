from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import application

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Takes a CV + job description, matches skills via embeddings + "
        "a vector database, and uses an LLM agent graph to generate a "
        "tailored CV, cover letter, and interview prep."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(application.router)


@app.on_event("startup")
def on_startup():
    os.makedirs(settings.upload_dir, exist_ok=True)
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# Serve the HTML/JS frontend. Mounted last so /api/* takes priority.
_candidate_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static")),
]
_static_dir = next((d for d in _candidate_dirs if os.path.isdir(d)), None)
if _static_dir:
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
