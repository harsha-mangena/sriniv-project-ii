"""Analytics API endpoints."""

import logging

from fastapi import APIRouter

from analysis.profile_builder import build_learning_profile
from db.database import get_session_history, get_skill_atom_scores, get_skill_atom_scores_normalized

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/profile")
async def get_profile(user_id: str = "default"):
    """Get user learning profile."""
    sessions = await get_session_history(user_id)
    atom_scores = await get_skill_atom_scores_normalized(user_id)
    profile = build_learning_profile(sessions, atom_scores=atom_scores)
    return profile


@router.get("/heatmap")
async def get_heatmap(user_id: str = "default"):
    """Get skill atom heatmap data."""
    atoms = await get_skill_atom_scores(user_id)
    return {"atoms": atoms}


@router.get("/history")
async def get_history(user_id: str = "default", limit: int = 20):
    """Get session history."""
    sessions = await get_session_history(user_id, limit)
    return {"sessions": sessions}


@router.get("/progress")
async def get_progress(user_id: str = "default"):
    """Get progress metrics over time."""
    sessions = await get_session_history(user_id, limit=50)

    # Build progress data
    progress = []
    for i, s in enumerate(reversed(sessions)):
        progress.append({
            "session_number": i + 1,
            "score": s.get("overall_score", 0),
            "mode": s.get("mode", "mock"),
            "date": s.get("started_at", ""),
            "questions": s.get("question_count", 0),
        })

    return {
        "progress": progress,
        "total_sessions": len(sessions),
        "avg_score": sum(p["score"] or 0 for p in progress) / max(len(progress), 1),
    }
