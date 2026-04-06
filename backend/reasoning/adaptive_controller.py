"""Adaptive difficulty controller.

Uses combined AoT atom precision and ToT tree coverage
signals to adjust interview difficulty in real time.
"""

import logging
from typing import Any

from config import DIFFICULTY_INCREASE_THRESHOLD, DIFFICULTY_DECREASE_THRESHOLD

logger = logging.getLogger(__name__)


class AdaptiveController:
    """Controls interview difficulty based on candidate performance."""

    def __init__(self):
        self.recent_scores: list[float] = []
        self.current_difficulty: int = 3  # 1-5 scale
        self.strategy: str = "bfs"  # bfs or dfs
        self.adjustments: list[dict] = []

    def update(self, overall_score: float, evaluation: dict[str, Any]) -> None:
        """Update controller with latest evaluation results.

        Decision matrix:
        - atom_precision > 0.85 → increase difficulty (DFS deeper)
        - atom_precision < 0.50 → decrease difficulty (ToT backtrack)
        - 0.50-0.85 → maintain (continue with follow-ups)
        """
        self.recent_scores.append(overall_score)
        avg_recent = sum(self.recent_scores[-5:]) / len(self.recent_scores[-5:])

        old_difficulty = self.current_difficulty
        old_strategy = self.strategy

        if avg_recent >= DIFFICULTY_INCREASE_THRESHOLD:
            # Candidate is strong → go deeper
            self.current_difficulty = min(5, self.current_difficulty + 1)
            self.strategy = "dfs"
            reason = "Strong performance — increasing difficulty and going deeper."
        elif avg_recent < DIFFICULTY_DECREASE_THRESHOLD:
            # Candidate is struggling → backtrack and simplify
            self.current_difficulty = max(1, self.current_difficulty - 1)
            self.strategy = "bfs"
            reason = "Needs reinforcement — adjusting difficulty and broadening topics."
        else:
            # Moderate performance → maintain and probe
            reason = "Moderate performance — maintaining current level."

        if old_difficulty != self.current_difficulty or old_strategy != self.strategy:
            self.adjustments.append({
                "from_difficulty": old_difficulty,
                "to_difficulty": self.current_difficulty,
                "from_strategy": old_strategy,
                "to_strategy": self.strategy,
                "trigger_score": overall_score,
                "avg_recent": round(avg_recent, 3),
                "reason": reason,
            })
            logger.info(
                "Adaptive adjustment: difficulty %d→%d, strategy %s→%s (%s)",
                old_difficulty, self.current_difficulty,
                old_strategy, self.strategy, reason,
            )

    def get_search_strategy(self) -> str:
        """Get current ToT search strategy."""
        return self.strategy

    def get_difficulty_filter(self) -> tuple[int, int]:
        """Get min/max difficulty range for question selection."""
        return max(1, self.current_difficulty - 1), min(5, self.current_difficulty + 1)

    def get_state(self) -> dict:
        """Get current controller state."""
        return {
            "current_difficulty": self.current_difficulty,
            "strategy": self.strategy,
            "recent_scores": self.recent_scores[-10:],
            "avg_recent": round(
                sum(self.recent_scores[-5:]) / max(len(self.recent_scores[-5:]), 1), 3
            ),
            "total_adjustments": len(self.adjustments),
            "last_adjustment": self.adjustments[-1] if self.adjustments else None,
        }
