"""User learning profile builder — aggregates performance across sessions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_learning_profile(session_history: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a comprehensive learning profile from session history.

    Args:
        session_history: List of session results with atom scores.

    Returns:
        Learning profile with strengths, weaknesses, trends.
    """
    if not session_history:
        return {
            "total_sessions": 0,
            "total_questions": 0,
            "avg_score": 0,
            "score_trend": [],
            "category_scores": {},
            "top_strengths": [],
            "top_weaknesses": [],
            "recommendations": [],
        }

    total_sessions = len(session_history)
    total_questions = sum(s.get("question_count", s.get("questions_count", 0)) for s in session_history)
    scores = [s.get("overall_score", 0) for s in session_history]
    avg_score = sum(scores) / max(len(scores), 1)

    # Category-level scores
    category_scores: dict[str, list[float]] = {}
    atom_scores: dict[str, list[float]] = {}

    for session in session_history:
        for q in session.get("questions", []):
            cat = q.get("category", "General")
            score = q.get("overall_score", 0)
            category_scores.setdefault(cat, []).append(score)
            for atom_id, atom_data in q.get("atom_scores", {}).items():
                atom_scores.setdefault(atom_id, []).append(
                    atom_data.get("score", 0) if isinstance(atom_data, dict) else atom_data
                )

    cat_averages = {
        cat: round(sum(scores) / len(scores), 3)
        for cat, scores in category_scores.items()
    }

    # Identify strengths and weaknesses
    sorted_cats = sorted(cat_averages.items(), key=lambda x: x[1])
    top_weaknesses = [{"category": c, "score": s} for c, s in sorted_cats[:3] if s < 0.7]
    top_strengths = [{"category": c, "score": s} for c, s in sorted_cats[-3:] if s >= 0.7]

    # Score trend (last 10 sessions)
    score_trend = [
        {"session": i + 1, "score": round(s, 3)}
        for i, s in enumerate(scores[-10:])
    ]

    # Generate recommendations
    recommendations = []
    for weakness in top_weaknesses:
        recommendations.append(
            f"Focus on {weakness['category']} — your average score is {weakness['score']:.0%}. "
            "Practice more questions in this area."
        )
    if avg_score >= 0.8:
        recommendations.append(
            "You're performing well overall! Consider tackling harder difficulty levels."
        )

    return {
        "total_sessions": total_sessions,
        "total_questions": total_questions,
        "avg_score": round(avg_score, 3),
        "score_trend": score_trend,
        "category_scores": cat_averages,
        "top_strengths": top_strengths,
        "top_weaknesses": top_weaknesses,
        "recommendations": recommendations,
    }
