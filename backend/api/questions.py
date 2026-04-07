"""Question generation API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from core.llm import get_llm
from db.database import get_document
from models.schemas import PrepGenerateRequest, PrepQuestionItem, PrepResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate-prep", response_model=PrepResponse)
async def generate_prep_questions(request: PrepGenerateRequest):
    """Generate preparation questions with model answers."""
    resume_doc = await get_document(request.resume_id)
    jd_doc = await get_document(request.jd_id)

    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if not jd_doc:
        raise HTTPException(status_code=404, detail="Job description not found.")

    resume_text = resume_doc["raw_text"][:2000]
    jd_text = jd_doc["raw_text"][:2000]
    n = request.num_questions

    prompt = f"""You are an expert interview coach. Generate {n} interview preparation questions for this candidate.

CANDIDATE RESUME (summary):
{resume_text}

JOB DESCRIPTION (summary):
{jd_text}

ROLE TYPE: {request.role_type}

Generate a mix of:
- Behavioral questions (STAR format) — ~30%
- Technical questions (DSA, coding) — ~25%
- System design questions — ~20%
- Role-specific questions — ~15%
- SQL/data questions — ~10%

For each question, provide:
1. The question text
2. Category (Behavioral/Technical/System Design/Role-Specific/SQL)
3. Difficulty (1-5)
4. A model answer tailored to THIS candidate's background
5. 3-5 talking points
6. Target skills being assessed

Return JSON:
{{
  "questions": [
    {{
      "question": "...",
      "category": "...",
      "difficulty": 3,
      "model_answer": "...",
      "talking_points": ["...", "..."],
      "target_skills": ["...", "..."]
    }}
  ]
}}"""

    result = await get_llm().generate_json(prompt, max_tokens=4096)
    questions_raw = result.get("questions", [])

    questions = []
    for q in questions_raw[:n]:
        questions.append(PrepQuestionItem(
            question=q.get("question", ""),
            category=q.get("category", "General"),
            difficulty=q.get("difficulty", 3),
            sample_answer=q.get("model_answer", ""),
            talking_points=q.get("talking_points", []),
            target_skills=q.get("target_skills", []),
        ))

    # Generate weakness analysis
    weakness_prompt = f"""Based on the resume and JD, identify the candidate's weak areas for interview preparation.

RESUME: {resume_text[:1000]}
JD: {jd_text[:1000]}

Return JSON:
{{
  "weak_areas": [
    {{"area": "...", "reason": "...", "priority": "high|medium|low"}}
  ],
  "preparation_tips": ["...", "..."]
}}"""

    weakness = await get_llm().generate_json(weakness_prompt)

    from analysis.match_scoring import calculate_match_score
    match = calculate_match_score(
        resume_doc["parsed_data"],
        jd_doc["parsed_data"],
    )

    return PrepResponse(
        session_id="prep_" + request.resume_id[:6],
        questions=questions,
        weakness_analysis=weakness,
        match_score=match,
        total_generated=len(questions),
    )
