"""Hybrid AoT+ToT interview engine — the core orchestrator.

Combines Tree of Thoughts for strategic question selection with
Atom of Thoughts for tactical answer evaluation and adaptive follow-ups.
"""

import hashlib
import json
import logging
from typing import Any, Optional

from reasoning.atom_of_thoughts import (
    contract_to_followup,
    decompose_to_dag,
    evaluate_atoms,
    generate_atom_feedback_summary,
)
from reasoning.tree_of_thoughts import (
    QuestionNode,
    QuestionTree,
    build_question_tree,
    personalize_question,
    select_next_question,
)
from reasoning.adaptive_controller import AdaptiveController
from reasoning.skill_atoms import SkillAtomTracker

logger = logging.getLogger(__name__)

# Fix 2.22: In-memory cache for question trees keyed by JD content hash
_question_tree_cache: dict[str, QuestionTree] = {}


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
        # Fix 2.9: Track consecutive failures per atom for loop prevention
        self._atom_failure_counts: dict[str, int] = {}
        # Fix 2.10: Track critical atoms that were never passed
        self._unpassed_critical_atoms: list[dict] = []

    async def initialize_session(
        self,
        resume_text: str,
        jd_text: str,
        role_type: str = "Software Engineer",
        question_templates: list[dict] | None = None,
    ) -> dict:
        """Initialize a new interview session.

        Builds the ToT question tree based on resume and JD analysis.
        Uses cached tree if same JD was seen before (Fix 2.22).
        """
        # Fix 2.22: Hash JD content and check cache
        jd_hash = hashlib.sha256(jd_text.encode()).hexdigest()
        if jd_hash in _question_tree_cache and not question_templates:
            logger.info("Using cached question tree for JD hash %s", jd_hash[:12])
            # Deep copy the cached tree by rebuilding from node data
            cached = _question_tree_cache[jd_hash]
            self.question_tree = QuestionTree()
            for node_id, node in cached.nodes.items():
                new_node = QuestionNode(
                    node_id=node.node_id,
                    category=node.category,
                    subcategory=node.subcategory,
                    question_template=node.question_template,
                    difficulty=node.difficulty,
                    target_atoms=node.target_atoms,
                    parent_id=node.parent_id,
                )
                self.question_tree.add_node(new_node)
        else:
            self.question_tree = await build_question_tree(
                jd_context=jd_text,
                resume_context=resume_text,
                role_type=role_type,
                templates=question_templates,
            )
            # Cache the tree for reuse
            if not question_templates:
                _question_tree_cache[jd_hash] = self.question_tree

        self.session_history = []
        self.follow_up_count = 0
        self._atom_failure_counts = {}
        self._unpassed_critical_atoms = []

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
        # Reset per-question atom failure tracking
        self._atom_failure_counts = {}

        result = {
            **self.current_question,
            "atoms_count": dag.get("total_atoms", 0),
            "is_follow_up": False,
        }

        # Fix 2.16: Propagate DAG warning to response
        if dag.get("warning"):
            result["warning"] = dag["warning"]

        return result

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

        # Fix 2.9: Track consecutive failures per atom
        for atom_id in evaluation.get("failed_atoms", []):
            self._atom_failure_counts[atom_id] = self._atom_failure_counts.get(atom_id, 0) + 1

        # Determine next action via AoT contraction
        next_action = await self._determine_next_action(evaluation)

        result = {
            "overall_score": overall_score,
            "atom_scores": evaluation["atom_scores"],
            "passed_atoms": evaluation["passed_atoms"],
            "failed_atoms": evaluation["failed_atoms"],
            "feedback_summary": feedback_summary,
            "next_action": next_action,
        }

        # Fix 2.16: Propagate warning
        if evaluation.get("warning"):
            result["warning"] = evaluation["warning"]

        return result

    async def _determine_next_action(self, evaluation: dict) -> dict:
        """Decide: follow-up (AoT contract), next question (ToT advance), or backtrack."""
        overall = evaluation["overall_score"]
        failed = evaluation["failed_atoms"]

        # Fix 2.9: Filter out atoms that have failed 2+ consecutive times (loop prevention)
        persistently_failed = [
            aid for aid in failed
            if self._atom_failure_counts.get(aid, 0) >= 2
        ]
        retriable_failed = [
            aid for aid in failed
            if self._atom_failure_counts.get(aid, 0) < 2
        ]

        if persistently_failed:
            logger.info(
                "Skipping persistently failed atoms (2+ consecutive failures): %s",
                persistently_failed,
            )

        # If there are retriable failed atoms and we haven't exceeded follow-up limit
        if retriable_failed and self.follow_up_count < self.max_follow_ups:
            # AoT Phase 3: Contract to follow-up question
            failed_details = []
            passed_details = []
            for atom in self.current_dag.get("atoms", []):
                aid = atom["id"]
                score_data = evaluation["atom_scores"].get(aid, {})
                detail = {**atom, "feedback": score_data.get("feedback", "")}
                if aid in retriable_failed:
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
                    "reason": f"Probing deeper into {len(retriable_failed)} areas that need work.",
                    "atoms_count": self.current_dag.get("total_atoms", 0),
                }

        # Fix 2.10: When max_follow_ups reached, log critical atoms never passed
        if self.follow_up_count >= self.max_follow_ups and failed:
            unpassed = []
            for atom in self.current_dag.get("atoms", []):
                if atom["id"] in failed:
                    unpassed.append({
                        "atom_id": atom["id"],
                        "label": atom.get("label", "Unknown"),
                        "last_score": evaluation["atom_scores"].get(atom["id"], {}).get("score", 0),
                    })
            if unpassed:
                self._unpassed_critical_atoms.extend(unpassed)
                logger.warning(
                    "Max follow-ups reached. Critical atoms never passed: %s",
                    [a["label"] for a in unpassed],
                )

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

        stats = {
            "questions_asked": len(self.session_history),
            "tree_coverage": coverage,
            "skill_profile": skill_profile,
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "adaptive_state": self.adaptive.get_state(),
        }

        # Fix 2.10: Include unpassed critical atoms in stats for analytics
        if self._unpassed_critical_atoms:
            stats["unpassed_critical_atoms"] = self._unpassed_critical_atoms

        return stats

    def serialize_state(self) -> dict:
        """Serialize engine state for DB persistence (Fix 2.11)."""
        tree_data = {}
        if self.question_tree:
            tree_data = {
                "nodes": {
                    nid: n.to_dict() for nid, n in self.question_tree.nodes.items()
                },
                "visit_history": self.question_tree.visit_history,
            }

        return {
            "question_tree": json.dumps(tree_data),
            "current_question": json.dumps(self.current_question) if self.current_question else "{}",
            "current_dag": json.dumps(self.current_dag) if self.current_dag else "{}",
            "follow_up_count": self.follow_up_count,
            "session_history": json.dumps(self.session_history),
            "skill_tracker_state": json.dumps({
                aid: {
                    "cumulative_score": atom["cumulative_score"],
                    "attempt_count": atom["attempt_count"],
                    "last_score": atom["last_score"],
                    "history": atom.get("history", []),
                }
                for aid, atom in self.skill_tracker.atoms.items()
                if atom["attempt_count"] > 0
            }),
            "adaptive_state": json.dumps(self.adaptive.get_state()),
            "atom_failure_counts": json.dumps(self._atom_failure_counts),
        }

    @classmethod
    def from_serialized_state(cls, state: dict) -> "HybridInterviewEngine":
        """Reconstruct engine from serialized DB state (Fix 2.12)."""
        engine = cls()

        # Restore question tree
        tree_data = json.loads(state.get("question_tree", "{}"))
        if tree_data and tree_data.get("nodes"):
            engine.question_tree = QuestionTree()
            for nid, ndata in tree_data["nodes"].items():
                node = QuestionNode(
                    node_id=ndata["node_id"],
                    category=ndata["category"],
                    subcategory=ndata["subcategory"],
                    question_template=ndata["question_template"],
                    difficulty=ndata["difficulty"],
                    target_atoms=ndata["target_atoms"],
                )
                node.visited = ndata.get("visited", False)
                node.score = ndata.get("score")
                engine.question_tree.add_node(node)
            engine.question_tree.visit_history = tree_data.get("visit_history", [])

        # Restore current question and DAG
        cq = json.loads(state.get("current_question", "{}"))
        engine.current_question = cq if cq else None
        cd = json.loads(state.get("current_dag", "{}"))
        engine.current_dag = cd if cd else None

        # Restore counters
        engine.follow_up_count = state.get("follow_up_count", 0)
        engine.session_history = json.loads(state.get("session_history", "[]"))

        # Restore skill tracker state
        tracker_state = json.loads(state.get("skill_tracker_state", "{}"))
        for aid, data in tracker_state.items():
            if aid in engine.skill_tracker.atoms:
                engine.skill_tracker.atoms[aid].update(data)
            else:
                engine.skill_tracker.atoms[aid] = {
                    "id": aid,
                    "label": aid,
                    "category": "",
                    "difficulty": 3,
                    "prerequisites": [],
                    **data,
                }

        # Restore adaptive state
        adaptive_data = json.loads(state.get("adaptive_state", "{}"))
        if adaptive_data:
            engine.adaptive.current_difficulty = adaptive_data.get("current_difficulty", 3)
            engine.adaptive.strategy = adaptive_data.get("strategy", "bfs")
            engine.adaptive.recent_scores = adaptive_data.get("recent_scores", [])

        # Restore atom failure counts
        engine._atom_failure_counts = json.loads(state.get("atom_failure_counts", "{}"))

        return engine
