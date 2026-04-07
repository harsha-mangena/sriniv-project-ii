"""Interview session management API endpoints."""

import json
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from core.llm import LLMResponseError
from db.database import (
    create_session,
    delete_session_state,
    get_document,
    get_session,
    get_session_state,
    save_answer,
    save_question,
    save_session_state,
    save_skill_atom_score,
    update_session,
)
from models.schemas import (
    AnswerEvaluationResponse,
    AnswerSubmitRequest,
    InterviewStartRequest,
    InterviewStartResponse,
    NextQuestionResponse,
    SessionEndResponse,
)
from reasoning.hybrid_engine import HybridInterviewEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# Active interview engines (in-memory, keyed by session_id)
active_engines: dict[str, HybridInterviewEngine] = {}
session_metadata: dict[str, dict] = {}
question_counters: dict[str, int] = {}


async def _persist_session_state(session_id: str, engine: HybridInterviewEngine) -> None:
    """Fix 2.11: Persist session state to DB after each state change."""
    try:
        state = engine.serialize_state()
        meta = session_metadata.get(session_id, {})
        await save_session_state(
            session_id=session_id,
            question_tree=state["question_tree"],
            current_question=state["current_question"],
            current_dag=state["current_dag"],
            follow_up_count=state["follow_up_count"],
            question_counter=question_counters.get(session_id, 0),
            session_history=state["session_history"],
            skill_tracker_state=state["skill_tracker_state"],
            adaptive_state=state["adaptive_state"],
            metadata=json.dumps(meta),
        )
    except Exception as e:
        logger.error("Failed to persist session state for %s: %s", session_id, e)


async def _try_recover_session(session_id: str) -> Optional[HybridInterviewEngine]:
    """Fix 2.13: Attempt to recover a session from DB before returning 404."""
    session = await get_session(session_id)
    if not session or session.get("status") != "active":
        return None

    state = await get_session_state(session_id)
    if not state:
        return None

    try:
        engine = HybridInterviewEngine.from_serialized_state(state)
        meta_str = state.get("metadata", "{}")
        meta = json.loads(meta_str) if meta_str else {}

        # Restore in-memory state
        active_engines[session_id] = engine
        session_metadata[session_id] = meta
        question_counters[session_id] = state.get("question_counter", 0)

        logger.info("Successfully recovered session %s from DB", session_id)
        return engine
    except Exception as e:
        logger.error("Failed to recover session %s: %s", session_id, e)
        return None


@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(request: InterviewStartRequest):
    """Start a new interview session."""
    # Load documents
    resume_doc = await get_document(request.resume_id)
    jd_doc = await get_document(request.jd_id)

    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume document not found.")
    if not jd_doc:
        raise HTTPException(status_code=404, detail="Job description document not found.")

    # Create session in DB
    session_id = await create_session(
        resume_id=request.resume_id,
        jd_id=request.jd_id,
        mode=request.mode,
    )

    # Initialize hybrid engine
    engine = HybridInterviewEngine()
    init_result = await engine.initialize_session(
        resume_text=resume_doc["raw_text"],
        jd_text=jd_doc["raw_text"],
        role_type=request.role_type,
    )

    # Store engine and metadata
    active_engines[session_id] = engine
    session_metadata[session_id] = {
        "resume_text": resume_doc["raw_text"],
        "jd_text": jd_doc["raw_text"],
        "resume_id": request.resume_id,
        "jd_id": request.jd_id,
        "started_at": datetime.utcnow().isoformat(),
    }
    question_counters[session_id] = 0

    # Get the first question
    first_q = await engine.get_next_question(
        resume_context=resume_doc["raw_text"][:500],
        jd_context=jd_doc["raw_text"][:500],
    )

    first_question_data = None
    if first_q:
        question_counters[session_id] += 1
        q_id = await save_question(
            session_id=session_id,
            question_text=first_q["question_text"],
            category=first_q.get("category", ""),
            difficulty=first_q.get("difficulty", 3),
            target_skills=first_q.get("target_atoms", []),
            evaluation_atoms={},
            sequence=question_counters[session_id],
        )
        first_question_data = {
            "question_id": q_id,
            **first_q,
        }

    # Fix 2.11: Persist initial state
    await _persist_session_state(session_id, engine)

    return InterviewStartResponse(
        session_id=session_id,
        status="active",
        total_questions=init_result.get("total_questions", 0),
        categories=init_result.get("categories", 0),
        first_question=first_question_data,
    )


@router.post("/answer", response_model=AnswerEvaluationResponse)
async def submit_answer(request: AnswerSubmitRequest):
    """Submit an answer for evaluation."""
    engine = active_engines.get(request.session_id)

    # Fix 2.13: Auto-recover from DB before returning 404
    if not engine:
        engine = await _try_recover_session(request.session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="No active session. Start an interview first.")

    if not request.answer_text.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    start_time = time.time()

    # Evaluate using AoT atomic decomposition
    evaluation = await engine.evaluate_answer(request.answer_text)
    elapsed = time.time() - start_time

    # Get current question info for saving
    current_q = engine.current_question
    q_id = current_q.get("node_id", "") if current_q else ""

    # Fix 2.6: If this is a follow-up, ensure the follow-up question is saved
    # as a proper question record before saving the answer
    next_action = evaluation.get("next_action", {})
    if next_action.get("action") == "follow_up" and next_action.get("question"):
        follow_up_q_id = await save_question(
            session_id=request.session_id,
            question_text=next_action["question"],
            category=current_q.get("category", "") if current_q else "",
            difficulty=current_q.get("difficulty", 3) if current_q else 3,
            target_skills=current_q.get("target_atoms", []) if current_q else [],
            evaluation_atoms={},
            sequence=question_counters.get(request.session_id, 0) + 1,
        )
        question_counters[request.session_id] = question_counters.get(request.session_id, 0) + 1

    # Fix 2.5: Validate question_id before saving answer
    if q_id:
        await save_answer(
            question_id=q_id,
            session_id=request.session_id,
            answer_text=request.answer_text,
            atom_scores=evaluation.get("atom_scores", {}),
            overall_score=evaluation.get("overall_score", 0),
            feedback=evaluation.get("feedback_summary", ""),
            follow_up=next_action.get("question", ""),
            time_taken=elapsed,
        )
    else:
        logger.warning("Skipping answer save: no valid question_id for session %s", request.session_id)

    # Fix 2.21: Write individual atom scores to normalized table
    for atom in (engine.current_dag or {}).get("atoms", []):
        atom_id = atom["id"]
        score_data = evaluation.get("atom_scores", {}).get(atom_id, {})
        score = score_data.get("score", 0)
        try:
            await save_skill_atom_score(
                user_id="default",
                session_id=request.session_id,
                question_id=q_id or "unknown",
                atom_id=atom_id,
                atom_name=atom.get("label", atom_id),
                category=current_q.get("category", "") if current_q else "",
                score=score,
                passed=score >= 0.7,
            )
        except Exception as e:
            logger.error("Failed to save atom score %s: %s", atom_id, e)

    # Fix 2.11: Persist state after evaluation
    await _persist_session_state(request.session_id, engine)

    return AnswerEvaluationResponse(
        overall_score=evaluation["overall_score"],
        atom_scores=evaluation["atom_scores"],
        passed_atoms=evaluation["passed_atoms"],
        failed_atoms=evaluation["failed_atoms"],
        feedback_summary=evaluation["feedback_summary"],
        next_action=evaluation["next_action"],
    )


@router.post("/next", response_model=NextQuestionResponse)
async def get_next_question(session_id: str):
    """Get the next question from the ToT tree."""
    engine = active_engines.get(session_id)

    # Fix 2.13: Auto-recover from DB before returning 404
    if not engine:
        engine = await _try_recover_session(session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="No active session found.")

    meta = session_metadata.get(session_id, {})
    next_q = await engine.get_next_question(
        resume_context=meta.get("resume_text", "")[:500],
        jd_context=meta.get("jd_text", "")[:500],
    )

    if not next_q:
        raise HTTPException(status_code=204, detail="No more questions. Interview complete.")

    question_counters[session_id] = question_counters.get(session_id, 0) + 1
    q_id = await save_question(
        session_id=session_id,
        question_text=next_q["question_text"],
        category=next_q.get("category", ""),
        difficulty=next_q.get("difficulty", 3),
        target_skills=next_q.get("target_atoms", []),
        evaluation_atoms={},
        sequence=question_counters[session_id],
    )

    # Fix 2.11: Persist state after getting next question
    await _persist_session_state(session_id, engine)

    return NextQuestionResponse(
        question_text=next_q["question_text"],
        category=next_q.get("category", "General"),
        subcategory=next_q.get("subcategory", ""),
        difficulty=next_q.get("difficulty", 3),
        atoms_count=next_q.get("atoms_count", 0),
        is_follow_up=next_q.get("is_follow_up", False),
        node_id=next_q.get("node_id"),
    )


@router.get("/session/{session_id}")
async def get_session_details(session_id: str):
    """Get session details and current stats."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    engine = active_engines.get(session_id)
    stats = engine.get_session_stats() if engine else {}

    return {
        "session": dict(session),
        "stats": stats,
        "questions_asked": question_counters.get(session_id, 0),
    }


@router.post("/end", response_model=SessionEndResponse)
async def end_interview(session_id: str):
    """End an interview session and get summary."""
    engine = active_engines.get(session_id)

    # Fix 2.13: Auto-recover from DB before returning 404
    if not engine:
        engine = await _try_recover_session(session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="No active session found.")

    stats = engine.get_session_stats()
    ended_at = datetime.utcnow()

    # Calculate overall score from skill profile
    skill_profile = stats.get("skill_profile", {})
    if isinstance(skill_profile, dict) and skill_profile:
        overall_score = sum(skill_profile.values()) / len(skill_profile)
    else:
        overall_score = 0.0

    # Update session in DB
    await update_session(
        session_id,
        status="completed",
        overall_score=overall_score,
        ended_at=ended_at.isoformat(),
    )

    # Calculate duration
    meta = session_metadata.get(session_id, {})
    started = meta.get("started_at", ended_at.isoformat())
    try:
        start_dt = datetime.fromisoformat(started)
        duration = (ended_at - start_dt).total_seconds() / 60
    except Exception:
        duration = 0

    # Clean up in-memory state
    active_engines.pop(session_id, None)
    session_metadata.pop(session_id, None)
    question_counters.pop(session_id, None)

    # Clean up persisted state
    await delete_session_state(session_id)

    # Build category scores from skill profile
    category_scores = {}
    for area in stats.get("weak_areas", []) + stats.get("strong_areas", []):
        cat = area.get("category", "")
        if cat:
            category_scores[cat] = area.get("score", 0)

    return SessionEndResponse(
        session_id=session_id,
        total_questions=stats.get("questions_asked", 0),
        overall_score=round(overall_score, 3),
        category_scores=category_scores,
        weak_areas=stats.get("weak_areas", []),
        strong_areas=stats.get("strong_areas", []),
        duration_minutes=round(duration, 1),
    )


@router.post("/recover/{session_id}")
async def recover_session(session_id: str):
    """Fix 2.12: Recover a session from persisted state after backend restart."""
    # Check if already active
    if session_id in active_engines:
        engine = active_engines[session_id]
        return {
            "status": "already_active",
            "session_id": session_id,
            "stats": engine.get_session_stats(),
        }

    engine = await _try_recover_session(session_id)
    if not engine:
        raise HTTPException(
            status_code=404,
            detail="Session not found or cannot be recovered. Start a new interview.",
        )

    return {
        "status": "recovered",
        "session_id": session_id,
        "stats": engine.get_session_stats(),
    }
