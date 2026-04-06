"""Job description parsing — extracts structured requirements."""

import logging
from typing import Any

from core.llm import get_llm

logger = logging.getLogger(__name__)


async def parse_job_description(text: str) -> dict[str, Any]:
    """Parse job description into structured data using LLM.

    Returns:
        Dict with requirements, responsibilities, keywords, etc.
    """
    prompt = f"""You are an expert job description analyst. Extract structured information from this JD.

JOB DESCRIPTION:
{text[:4000]}

Extract and return as JSON:
{{
  "title": "<job title>",
  "company": "<company name if mentioned>",
  "level": "<entry/mid/senior/staff/principal>",
  "role_type": "<SDE/Data Engineer/DevOps/Frontend/Backend/Full Stack/ML/QA/etc>",
  "required_skills": [
    {{
      "skill": "...",
      "importance": "must_have|nice_to_have",
      "category": "language|framework|tool|concept|soft_skill"
    }}
  ],
  "responsibilities": ["...", "..."],
  "requirements": {{
    "years_experience": <number or null>,
    "education": "<required education>",
    "certifications": ["..."]
  }},
  "keywords": ["...", "..."],
  "interview_focus_areas": ["...", "..."],
  "culture_signals": ["...", "..."]
}}

Be thorough. Extract every technical requirement and responsibility."""

    result = await get_llm().generate_json(prompt)
    if "required_skills" not in result:
        result = {
            "title": "",
            "company": "",
            "level": "mid",
            "role_type": "Software Engineer",
            "required_skills": [],
            "responsibilities": [],
            "requirements": {"years_experience": None, "education": "", "certifications": []},
            "keywords": [],
            "interview_focus_areas": [],
            "culture_signals": [],
            "parse_error": "Failed to parse job description.",
        }
    return result


def get_required_skills_flat(parsed_jd: dict) -> list[str]:
    """Get a flat list of all required skills from a parsed JD."""
    return [s["skill"] for s in parsed_jd.get("required_skills", []) if isinstance(s, dict)]
