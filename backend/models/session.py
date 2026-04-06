"""Session-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class InterviewSession:
    """In-memory representation of an active interview session."""
    id: str
    user_id: str
    resume_id: str
    jd_id: str
    mode: str  # mock, prep, realtime
    status: str = "active"  # active, completed, abandoned
    overall_score: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    questions_asked: list[dict[str, Any]] = field(default_factory=list)
    resume_text: str = ""
    jd_text: str = ""
    parsed_resume: dict = field(default_factory=dict)
    parsed_jd: dict = field(default_factory=dict)
