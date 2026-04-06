"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# === Document Schemas ===

class DocumentUploadRequest(BaseModel):
    text: str = Field(..., description="Document text content")
    doc_type: str = Field(..., description="Type: 'resume' or 'job_description'")
    filename: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    doc_type: str
    parsed_data: dict[str, Any]
    match_score: Optional[dict] = None
    created_at: str


# === Interview Schemas ===

class InterviewStartRequest(BaseModel):
    resume_id: str
    jd_id: str
    mode: str = Field(default="mock", description="mock, prep, or realtime")
    role_type: str = Field(default="Software Engineer")

class InterviewStartResponse(BaseModel):
    session_id: str
    status: str
    total_questions: int
    categories: int
    first_question: Optional[dict] = None

class AnswerSubmitRequest(BaseModel):
    session_id: str
    answer_text: str

class AnswerEvaluationResponse(BaseModel):
    overall_score: float
    atom_scores: dict[str, Any]
    passed_atoms: list[str]
    failed_atoms: list[str]
    feedback_summary: str
    next_action: dict[str, Any]

class NextQuestionResponse(BaseModel):
    question_text: str
    category: str
    subcategory: str
    difficulty: int
    atoms_count: int
    is_follow_up: bool
    node_id: Optional[str] = None

class SessionEndResponse(BaseModel):
    session_id: str
    total_questions: int
    overall_score: float
    category_scores: dict[str, float]
    weak_areas: list[dict]
    strong_areas: list[dict]
    duration_minutes: float


# === Prep Schemas ===

class PrepGenerateRequest(BaseModel):
    resume_id: str
    jd_id: str
    num_questions: int = Field(default=30, ge=10, le=50)
    role_type: str = Field(default="Software Engineer")

class PrepQuestionItem(BaseModel):
    question: str
    category: str
    difficulty: int
    model_answer: str
    talking_points: list[str]
    target_skills: list[str]

class PrepResponse(BaseModel):
    session_id: str
    questions: list[PrepQuestionItem]
    weakness_analysis: dict[str, Any]
    match_score: dict[str, Any]
    total_generated: int


# === Analytics Schemas ===

class SkillHeatmapItem(BaseModel):
    id: str
    label: str
    category: str
    score: float
    attempts: int
    difficulty: int

class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_questions: int
    avg_score: float
    score_trend: list[dict]
    category_scores: dict[str, float]
    top_strengths: list[dict]
    top_weaknesses: list[dict]
    recommendations: list[str]

class SessionHistoryItem(BaseModel):
    id: str
    mode: str
    overall_score: Optional[float]
    questions_count: int
    started_at: str
    ended_at: Optional[str]


# === Evaluation Schemas ===

class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    context: Optional[str] = None

class AtomBreakdownResponse(BaseModel):
    question: str
    total_atoms: int
    atoms: list[dict[str, Any]]
