"""Skill gap analysis between resume and job description."""

import logging
from typing import Any

from core.llm import get_llm

logger = logging.getLogger(__name__)


async def analyze_skill_gap(
    parsed_resume: dict[str, Any],
    parsed_jd: dict[str, Any],
) -> dict[str, Any]:
    """Perform deep skill gap analysis between resume and JD.

    Returns:
        Detailed gap analysis with matched skills, missing skills,
        and recommendations.
    """
    resume_skills = parsed_resume.get("skills", {})
    jd_skills = parsed_jd.get("required_skills", [])
    experience = parsed_resume.get("experience", [])

    prompt = f"""You are an expert career advisor. Analyze the gap between this candidate's skills and the job requirements.

CANDIDATE SKILLS:
{resume_skills}

CANDIDATE EXPERIENCE:
{experience[:5]}

JOB REQUIRED SKILLS:
{jd_skills}

JOB RESPONSIBILITIES:
{parsed_jd.get('responsibilities', [])}

Perform a detailed analysis and return JSON:
{{
  "matched_skills": [
    {{
      "skill": "...",
      "candidate_level": "beginner|intermediate|advanced|expert",
      "required_level": "beginner|intermediate|advanced|expert",
      "gap": "none|small|medium|large"
    }}
  ],
  "missing_skills": [
    {{
      "skill": "...",
      "importance": "must_have|nice_to_have",
      "learning_difficulty": "easy|medium|hard",
      "suggested_resources": "..."
    }}
  ],
  "strengths": ["<areas where candidate exceeds requirements>"],
  "overall_readiness": "<percentage 0-100>",
  "top_focus_areas": ["<most important gaps to address>"],
  "interview_risk_areas": ["<topics likely to be challenging in interview>"]
}}"""

    result = await get_llm().generate_json(prompt)
    if "matched_skills" not in result:
        result = {
            "matched_skills": [],
            "missing_skills": [],
            "strengths": [],
            "overall_readiness": 50,
            "top_focus_areas": [],
            "interview_risk_areas": [],
        }
    return result
