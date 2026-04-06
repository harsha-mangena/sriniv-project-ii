"""Skill Atom Registry and Tracker.

Maintains the candidate's skill profile as a collection of atomic
competencies, updated after each evaluation cycle.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Load skill taxonomy
TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "skill_taxonomy.json"


def load_taxonomy() -> dict:
    """Load the predefined skill atom taxonomy."""
    try:
        with open(TAXONOMY_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Skill taxonomy not found at %s, using empty taxonomy.", TAXONOMY_PATH)
        return {"categories": []}


class SkillAtomTracker:
    """Tracks per-atom skill scores across interview sessions."""

    def __init__(self):
        self.atoms: dict[str, dict[str, Any]] = {}
        self.taxonomy = load_taxonomy()
        self._init_from_taxonomy()

    def _init_from_taxonomy(self) -> None:
        """Initialize atoms from taxonomy with zero scores."""
        for category in self.taxonomy.get("categories", []):
            cat_name = category.get("name", "")
            for atom in category.get("atoms", []):
                atom_id = atom.get("id", "")
                self.atoms[atom_id] = {
                    "id": atom_id,
                    "label": atom.get("label", ""),
                    "category": cat_name,
                    "difficulty": atom.get("difficulty", 3),
                    "prerequisites": atom.get("prerequisites", []),
                    "cumulative_score": 0.0,
                    "attempt_count": 0,
                    "last_score": None,
                    "history": [],
                }

    def update_from_evaluation(
        self,
        dag: dict[str, Any],
        evaluation: dict[str, Any],
        category: str = "",
    ) -> None:
        """Update skill atoms from an AoT evaluation result."""
        atom_scores = evaluation.get("atom_scores", {})
        dag_atoms = dag.get("atoms", [])

        for dag_atom in dag_atoms:
            atom_id = dag_atom.get("id", "")
            label = dag_atom.get("label", "")
            score_data = atom_scores.get(atom_id, {})
            score = score_data.get("score", 0.0)

            # Try to match to taxonomy or create dynamic atom
            matched_id = self._match_to_taxonomy(label, category)
            track_id = matched_id or f"dynamic_{label.lower().replace(' ', '_')}"

            if track_id not in self.atoms:
                self.atoms[track_id] = {
                    "id": track_id,
                    "label": label,
                    "category": category,
                    "difficulty": 3,
                    "prerequisites": [],
                    "cumulative_score": 0.0,
                    "attempt_count": 0,
                    "last_score": None,
                    "history": [],
                }

            atom = self.atoms[track_id]
            atom["attempt_count"] += 1
            atom["last_score"] = score
            atom["history"].append(score)
            # Exponential moving average for cumulative score
            alpha = 0.3
            atom["cumulative_score"] = (
                alpha * score + (1 - alpha) * atom["cumulative_score"]
            )

    def _match_to_taxonomy(self, label: str, category: str) -> Optional[str]:
        """Try to match a dynamic atom label to a taxonomy atom."""
        label_lower = label.lower()
        for cat in self.taxonomy.get("categories", []):
            if category and cat.get("name", "").lower() != category.lower():
                continue
            for atom in cat.get("atoms", []):
                if (
                    atom.get("label", "").lower() in label_lower
                    or label_lower in atom.get("label", "").lower()
                ):
                    return atom["id"]
        return None

    def get_profile_scores(self) -> dict[str, float]:
        """Get current skill profile as {atom_id: score}."""
        return {
            aid: atom["cumulative_score"]
            for aid, atom in self.atoms.items()
            if atom["attempt_count"] > 0
        }

    def get_weak_areas(self, threshold: float = 0.6) -> list[dict]:
        """Get atoms with scores below threshold."""
        weak = []
        for aid, atom in self.atoms.items():
            if atom["attempt_count"] > 0 and atom["cumulative_score"] < threshold:
                weak.append({
                    "id": aid,
                    "label": atom["label"],
                    "category": atom["category"],
                    "score": round(atom["cumulative_score"], 3),
                    "attempts": atom["attempt_count"],
                })
        weak.sort(key=lambda x: x["score"])
        return weak

    def get_strong_areas(self, threshold: float = 0.8) -> list[dict]:
        """Get atoms with scores above threshold."""
        strong = []
        for aid, atom in self.atoms.items():
            if atom["attempt_count"] > 0 and atom["cumulative_score"] >= threshold:
                strong.append({
                    "id": aid,
                    "label": atom["label"],
                    "category": atom["category"],
                    "score": round(atom["cumulative_score"], 3),
                    "attempts": atom["attempt_count"],
                })
        strong.sort(key=lambda x: x["score"], reverse=True)
        return strong

    def get_unattempted(self) -> list[dict]:
        """Get atoms that have never been assessed."""
        return [
            {"id": aid, "label": atom["label"], "category": atom["category"]}
            for aid, atom in self.atoms.items()
            if atom["attempt_count"] == 0
        ]

    def get_heatmap_data(self) -> list[dict]:
        """Get data formatted for a skill heatmap visualization."""
        heatmap = []
        for aid, atom in self.atoms.items():
            heatmap.append({
                "id": aid,
                "label": atom["label"],
                "category": atom["category"],
                "score": round(atom["cumulative_score"], 3),
                "attempts": atom["attempt_count"],
                "difficulty": atom.get("difficulty", 3),
            })
        return heatmap
