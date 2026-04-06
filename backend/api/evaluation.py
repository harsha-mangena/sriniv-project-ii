"""Answer evaluation API endpoints."""

import logging

from fastapi import APIRouter

from models.schemas import AtomBreakdownResponse, EvaluateAnswerRequest
from reasoning.atom_of_thoughts import decompose_to_dag, evaluate_atoms, generate_atom_feedback_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/answer")
async def evaluate_single_answer(request: EvaluateAnswerRequest):
    """Evaluate a single answer using AoT atomic decomposition."""
    # Decompose question into atoms
    dag = await decompose_to_dag(request.question, context=request.context or "")

    # Evaluate answer
    evaluation = await evaluate_atoms(request.question, request.answer, dag)

    # Generate feedback
    feedback = await generate_atom_feedback_summary(request.question, evaluation, dag)

    return {
        "question": request.question,
        "overall_score": evaluation["overall_score"],
        "atom_scores": evaluation["atom_scores"],
        "passed_atoms": evaluation["passed_atoms"],
        "failed_atoms": evaluation["failed_atoms"],
        "feedback": feedback,
        "dag": dag,
    }


@router.post("/decompose", response_model=AtomBreakdownResponse)
async def decompose_question(question: str, context: str = ""):
    """Get atom breakdown for a question without evaluating an answer."""
    dag = await decompose_to_dag(question, context)
    return AtomBreakdownResponse(
        question=question,
        total_atoms=dag.get("total_atoms", 0),
        atoms=dag.get("atoms", []),
    )
