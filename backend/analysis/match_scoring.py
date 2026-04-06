"""Resume-JD match scoring."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def calculate_match_score(
    parsed_resume: dict[str, Any],
    parsed_jd: dict[str, Any],
) -> dict[str, Any]:
    """Calculate match score between resume and job description.

    Uses keyword overlap and weighted scoring.
    """
    # Flatten resume skills
    resume_skills_raw = parsed_resume.get("skills", {})
    resume_skills = set()
    for category in resume_skills_raw.values():
        if isinstance(category, list):
            for skill in category:
                resume_skills.add(skill.lower().strip())

    # Get JD requirements
    jd_skills = parsed_jd.get("required_skills", [])
    must_have = []
    nice_to_have = []
    for s in jd_skills:
        if isinstance(s, dict):
            skill_name = s.get("skill", "").lower().strip()
            if s.get("importance") == "must_have":
                must_have.append(skill_name)
            else:
                nice_to_have.append(skill_name)
        elif isinstance(s, str):
            must_have.append(s.lower().strip())

    # Calculate matches
    must_have_matched = [s for s in must_have if any(s in rs or rs in s for rs in resume_skills)]
    nice_have_matched = [s for s in nice_to_have if any(s in rs or rs in s for rs in resume_skills)]

    # Weighted scoring: must_have = 70%, nice_to_have = 30%
    must_score = len(must_have_matched) / max(len(must_have), 1)
    nice_score = len(nice_have_matched) / max(len(nice_to_have), 1)
    overall = must_score * 0.7 + nice_score * 0.3

    # Experience match
    required_years = parsed_jd.get("requirements", {}).get("years_experience")
    candidate_years = parsed_resume.get("total_years_experience", 0)
    experience_match = True
    if required_years and candidate_years:
        experience_match = candidate_years >= required_years

    return {
        "overall_score": round(overall * 100, 1),
        "must_have_score": round(must_score * 100, 1),
        "nice_to_have_score": round(nice_score * 100, 1),
        "must_have_matched": must_have_matched,
        "must_have_missing": [s for s in must_have if s not in must_have_matched],
        "nice_to_have_matched": nice_have_matched,
        "experience_match": experience_match,
        "total_must_have": len(must_have),
        "total_nice_to_have": len(nice_to_have),
    }
