"""Resume parsing — extracts structured data from resume text/PDF."""

import logging
from pathlib import Path
from typing import Any

from core.llm import llm

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text.strip()
    except ImportError:
        logger.warning("PyMuPDF not installed. Cannot parse PDF.")
        return ""
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        return ""


async def parse_resume(text: str) -> dict[str, Any]:
    """Parse resume text into structured data using LLM.

    Returns:
        Dict with skills, experience, projects, achievements, education.
    """
    prompt = f"""You are an expert resume parser. Extract structured information from this resume.

RESUME TEXT:
{text[:4000]}

Extract and return as JSON:
{{
  "name": "<full name>",
  "email": "<email if found>",
  "phone": "<phone if found>",
  "summary": "<1-2 sentence professional summary>",
  "skills": {{
    "programming_languages": ["Python", "Java", ...],
    "frameworks": ["React", "FastAPI", ...],
    "tools": ["Docker", "Git", ...],
    "databases": ["PostgreSQL", "Redis", ...],
    "cloud": ["AWS", "GCP", ...],
    "other": ["Agile", "CI/CD", ...]
  }},
  "experience": [
    {{
      "company": "...",
      "title": "...",
      "duration": "...",
      "highlights": ["...", "..."]
    }}
  ],
  "projects": [
    {{
      "name": "...",
      "description": "...",
      "technologies": ["...", "..."]
    }}
  ],
  "education": [
    {{
      "institution": "...",
      "degree": "...",
      "year": "..."
    }}
  ],
  "achievements": ["...", "..."],
  "total_years_experience": <number>
}}

Be thorough. Extract every skill, project, and achievement mentioned."""

    result = await llm.generate_json(prompt)
    if "skills" not in result:
        result = {
            "name": "",
            "skills": {"programming_languages": [], "frameworks": [], "tools": [], "databases": [], "cloud": [], "other": []},
            "experience": [],
            "projects": [],
            "education": [],
            "achievements": [],
            "total_years_experience": 0,
            "parse_error": "Failed to parse resume. Please check the format.",
        }
    return result


def get_all_skills_flat(parsed_resume: dict) -> list[str]:
    """Flatten all skills from a parsed resume into a single list."""
    skills = parsed_resume.get("skills", {})
    all_skills = []
    for category in skills.values():
        if isinstance(category, list):
            all_skills.extend(category)
    return all_skills
