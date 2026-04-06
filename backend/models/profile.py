"""User profile data models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserProfile:
    """User learning profile aggregated across sessions."""
    user_id: str
    total_sessions: int = 0
    total_questions_answered: int = 0
    avg_score: float = 0.0
    skill_scores: dict[str, float] = field(default_factory=dict)
    weak_areas: list[str] = field(default_factory=list)
    strong_areas: list[str] = field(default_factory=list)
    session_history: list[dict[str, Any]] = field(default_factory=list)
