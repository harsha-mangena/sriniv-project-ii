"""User learning profile builder — aggregates performance across sessions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_learning_profile(
    session_history: list[dict[str, Any]],
    atom_scores: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a comprehensive learning profile from session history.

    Args:
        session_history: List of flat session rows from get_session_history().
            Each row has: id, user_id, resume_id, jd_id, mode, status,
            overall_score, started_at, ended_at, question_count.
        atom_scores: Optional list of aggregated atom score rows from
            get_skill_atom_scores_normalized(). Each row has: atom_id,
            atom_name, category, avg_score, attempts, times_passed.

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
    total_questions = sum(
        s.get("question_count", s.get("questions_count", 0)) or 0
        for s in session_history
    )
    scores = [s.get("overall_score", 0) or 0 for s in session_history]
    avg_score = sum(scores) / max(len(scores), 1)

    # Build category scores from normalized atom_scores if available
    category_scores: dict[str, list[float]] = {}

    if atom_scores:
        for row in atom_scores:
            cat = row.get("category", "General")
            score = row.get("avg_score", 0) or 0
            category_scores.setdefault(cat, []).append(score)

    cat_averages = {
        cat: round(sum(vals) / len(vals), 3)
        for cat, vals in category_scores.items()
        if vals
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
