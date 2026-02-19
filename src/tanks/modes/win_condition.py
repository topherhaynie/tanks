"""Win condition definitions for tournament matches."""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.core.game import Game


class WinConditionType(Enum):
    """Types of win conditions for matches."""

    LAST_ALIVE = "last_alive"  # Last tank standing wins
    TIME_LIMIT = "time_limit"  # Most kills/damage after time expires
    ELIMINATION = "elimination"  # Reach target score or eliminate opponents


@dataclass
class WinCondition:
    """Win condition for a match.

    Attributes:
        type: Type of win condition.
        time_limit_seconds: Maximum match duration (for TIME_LIMIT type).
        target_kills: Target kill count (for ELIMINATION type).

    """

    type: WinConditionType
    time_limit_seconds: float = 300.0  # 5 minutes default
    target_kills: int = 5

    def check_match_won(self, game: "Game") -> tuple[bool, list[int]]:
        """Check if match has been won and return winner tank indices.

        Args:
            game: Current game state.

        Returns:
            Tuple of (match_won, winner_indices). If match not won,
            winner_indices is empty.

        """
        if self.type == WinConditionType.LAST_ALIVE:
            return self._check_last_alive(game)
        elif self.type == WinConditionType.TIME_LIMIT:
            return self._check_time_limit(game)
        elif self.type == WinConditionType.ELIMINATION:
            return self._check_elimination(game)

        return False, []

    def _check_last_alive(self, game: "Game") -> tuple[bool, list[int]]:
        """Check if only one tank remains alive.

        Args:
            game: Current game state.

        Returns:
            Tuple of (match_won, winner_indices).

        """
        alive_tanks = [i for i, tank in enumerate(game.state.tanks) if tank.active]

        if len(alive_tanks) == 1:
            return True, alive_tanks
        if len(alive_tanks) == 0:
            # Tie - last alive tank died at same time
            return True, []

        return False, []

    def _check_time_limit(self, game: "Game") -> tuple[bool, list[int]]:
        """Check if time limit has been reached.

        Args:
            game: Current game state.

        Returns:
            Tuple of (match_won, winner_indices). Winners are tanks with most kills.

        """
        if game.elapsed_time >= self.time_limit_seconds:
            # Match ends - winner is tank with most kills
            if not game.state.tanks:
                return True, []

            max_kills = max(
                (tank.kills for tank in game.state.tanks if tank.active),
                default=0,
            )
            winners = [
                i
                for i, tank in enumerate(game.state.tanks)
                if tank.active and tank.kills == max_kills
            ]
            return True, winners if winners else []

        return False, []

    def _check_elimination(self, game: "Game") -> tuple[bool, list[int]]:
        """Check if any tank has reached target kills.

        Args:
            game: Current game state.

        Returns:
            Tuple of (match_won, winner_indices).

        """
        winners = [
            i
            for i, tank in enumerate(game.state.tanks)
            if tank.kills >= self.target_kills
        ]

        if winners:
            return True, winners

        return False, []

    def get_description(self) -> str:
        """Get human-readable description of win condition.

        Returns:
            Description string.

        """
        if self.type == WinConditionType.LAST_ALIVE:
            return "Last tank standing"
        elif self.type == WinConditionType.TIME_LIMIT:
            return f"Time limit: {self.time_limit_seconds:.0f}s (most kills wins)"
        elif self.type == WinConditionType.ELIMINATION:
            return f"First to {self.target_kills} kills"

        return "Unknown"

    def update_for_elapsed_time(self, elapsed: float) -> float:
        """Get time remaining until condition is satisfied.

        Args:
            elapsed: Elapsed time in seconds.

        Returns:
            Time remaining (-1 if N/A for this condition).

        """
        if self.type == WinConditionType.TIME_LIMIT:
            remaining = self.time_limit_seconds - elapsed
            return max(0, remaining)

        return -1
