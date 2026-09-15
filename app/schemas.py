from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SkillMatch(BaseModel):
    requirement: str
    matched_cv_evidence: str
    similarity: float
    strength: str  # "strong" | "partial" | "weak"


class InterviewQuestion(BaseModel):
    question: str
    category: str  # "technical" | "behavioral" | "gap-probe"
    talking_points: str


class ApplicationCreateResponse(BaseModel):
    id: str
    status: str


class ApplicationResultResponse(BaseModel):
    id: str
    created_at: datetime
    job_title: Optional[str] = None
    status: str
    error_message: Optional[str] = None

    match_score: float = 0.0
    skill_matches: list[SkillMatch] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)

    tailored_cv_sections: dict = Field(default_factory=dict)
    cover_letter: Optional[str] = None
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)

    class Config:
        from_attributes = True
