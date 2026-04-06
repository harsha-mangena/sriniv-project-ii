"""Hybrid AoT+ToT interview engine — the core orchestrator.

Combines Tree of Thoughts for strategic question selection with
Atom of Thoughts for tactical answer evaluation and adaptive follow-ups.
"""

import logging
from typing import Any, Optional

from reasoning.atom_of_thoughts import (
    contract_to_followup,
    decompose_to_dag,
    evaluate_atoms,
    generate_atom_feedback_summary,
)
from reasoning.tree_of_thoughts import (
    QuestionTree,
    build_question_tree,
    personalize_question,
    select_next_question,
)
from reasoning.adaptive_controller import AdaptiveController
from reasoning.skill_atoms import SkillAtomTracker

logger = logging.getLogger(__name__)


class HybridInterviewEngine:
    """Orchestrates the full AoT+ToT interview loop.

    ToT Layer: Decides WHAT to ask (strategic question selection).
    AoT Layer: Decides HOW to evaluate (atomic answer decomposition).
    Adaptive Controller: Decides difficulty adjustments.
    """

    def __init__(self):
        self.question_tree: Optional[QuestionTree] = None
        self.skill_tracker = SkillAtomTracker()
        self.adaptive = AdaptiveController()
        self.session_history: list[str] = []
        self.current_question: Optional[dict] = None
        self.current_dag: Optional[dict] = None
        self.follow_up_count: int = 0
        self.max_follow_ups: int = 3

    async def initialize_session(
        self,
        resume_text: str,
        jd_text: str,
        role_type: str = "Software Engineer",
        question_templates: list[dict] | None = None,
    ) -> dict:
        """Initialize a new interview session.

        Builds the ToT question tree based on resume and JD analysis.
        """
        self.question_tree = await build_question_tree(
            jd_context=jd_text,
            resume_context=resume_text,
            role_type=role_type,
            templates=question_templates,
        )
        self.session_history = []
        self.follow_up_count = 0

        coverage = self.question_tree.get_coverage_stats()
        logger.info(
            "Session initialized: %d questions across %d categories",
            coverage["total"],
            coverage["categories_total"],
        )
        return {
            "status": "ready",
            "total_questions": coverage["total"],
            "categories": coverage["categories_total"],
        }

    async def get_next_question(
        self,
        resume_context: str = "",
        jd_context: str = "",
    ) -> Optional[dict]:
        """Get the next question using ToT selection.

        Returns:
            Question dict with text, category, difficulty, atoms, etc.
        """
        if self.question_tree is None:
            raise RuntimeError("Session not initialized. Call initialize_session first.")

        skill_profile = self.skill_tracker.get_profile_scores()

        # Determine search strategy based on adaptive controller
        strategy = self.adaptive.get_search_strategy()

        node = await select_next_question(
            tree=self.question_tree,
            skill_profile=skill_profile,
            session_history=self.session_history,
            strategy=strategy,
        )

        if node is None:
            return None

        # Personalize the question template
        question_text = await personalize_question(
            template=node.question_template,
            resume_context=resume_context,
            jd_context=jd_context,
        )

        # Pre-decompose the question into atoms (AoT Phase 1)
        dag = await decompose_to_dag(question_text, context=jd_context)

        self.current_question = {
            "node_id": node.node_id,
            "question_text": question_text,
            "category": node.category,
            "subcategory": node.subcategory,
            "difficulty": node.difficulty,
            "target_atoms": node.target_atoms,
        }
        self.current_dag = dag
        self.follow_up_count = 0

        return {
            **self.current_question,
            "atoms_count": dag.get("total_atoms", 0),
            "is_follow_up": False,
        }

    async def evaluate_answer(self, answer_text: str) -> dict[str, Any]:
        """Evaluate the candidate's answer using AoT atomic decomposition.

        Returns:
            Evaluation results with per-atom scores, feedback, and next action.
        """
        if self.current_question is None or self.current_dag is None:
            raise RuntimeError("No active question. Call get_next_question first.")

        question = self.current_question["question_text"]

        # AoT Phase 2: Evaluate answer atom-by-atom
        evaluation = await evaluate_atoms(question, answer_text, self.current_dag)

        # Update skill tracker with atom scores
        self.skill_tracker.update_from_evaluation(
            self.current_dag,
            evaluation,
            self.current_question.get("category", ""),
        )

        # Generate human-readable feedback
        feedback_summary = await generate_atom_feedback_summary(
            question, evaluation, self.current_dag
        )

        # Mark the ToT node as visited
        overall_score = evaluation["overall_score"]
        if self.question_tree and self.current_question["node_id"]:
            self.question_tree.mark_visited(
                self.current_question["node_id"], overall_score
            )
            self.session_history.append(self.current_question["node_id"])

        # Update adaptive controller
        self.adaptive.update(overall_score, evaluation)

        # Determine next action via AoT contraction
        next_action = await self._determine_next_action(evaluation)

        return {
            "overall_score": overall_score,
            "atom_scores": evaluation["atom_scores"],
            "passed_atoms": evaluation["passed_atoms"],
            "failed_atoms": evaluation["failed_atoms"],
            "feedback_summary": feedback_summary,
            "next_action": next_action,
        }

    async def _determine_next_action(self, evaluation: dict) -> dict:
        """Decide: follow-up (AoT contract), next question (ToT advance), or backtrack."""
        overall = evaluation["overall_score"]
        failed = evaluation["failed_atoms"]

        # If there are failed atoms and we haven't exceeded follow-up limit
        if failed and self.follow_up_count < self.max_follow_ups:
            # AoT Phase 3: Contract to follow-up question
            failed_details = []
            passed_details = []
            for atom in self.current_dag.get("atoms", []):
                aid = atom["id"]
                score_data = evaluation["atom_scores"].get(aid, {})
                detail = {**atom, "feedback": score_data.get("feedback", "")}
                if aid in failed:
                    failed_details.append(detail)
                else:
                    passed_details.append(detail)

            follow_up = await contract_to_followup(
                self.current_question["question_text"],
                failed_details,
                passed_details,
            )

            if follow_up:
                self.follow_up_count += 1
                # Re-decompose the follow-up (it's a new atomic question)
                self.current_dag = await decompose_to_dag(follow_up)
                self.current_question["question_text"] = follow_up

                return {
                    "action": "follow_up",
                    "question": follow_up,
                    "reason": f"Probing deeper into {len(failed)} areas that need work.",
                    "atoms_count": self.current_dag.get("total_atoms", 0),
                }

        # If score is high enough or no more follow-ups, move to next question
        if overall >= 0.85:
            return {
                "action": "next_question",
                "reason": "Great job! Moving to the next topic.",
            }
        elif overall < 0.50:
            # ToT backtrack: the topic may be too advanced
            if self.question_tree:
                backtrack_node = self.question_tree.backtrack()
                if backtrack_node:
                    return {
                        "action": "backtrack",
                        "reason": "Let's try a different angle on this topic.",
                        "backtrack_to": backtrack_node.node_id,
                    }
            return {
                "action": "next_question",
                "reason": "Let's move on and revisit this area later.",
            }
        else:
            return {
                "action": "next_question",
                "reason": "Good effort. Let's explore another area.",
            }

    def get_session_stats(self) -> dict:
        """Get current session statistics."""
        coverage = self.question_tree.get_coverage_stats() if self.question_tree else {}
        skill_profile = self.skill_tracker.get_profile_scores()
        weak_areas = self.skill_tracker.get_weak_areas()
        strong_areas = self.skill_tracker.get_strong_areas()

        return {
            "questions_asked": len(self.session_history),
            "tree_coverage": coverage,
            "skill_profile": skill_profile,
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "adaptive_state": self.adaptive.get_state(),
        }
