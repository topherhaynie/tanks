"""Single match management for tournament mode."""

from dataclasses import dataclass, field
from enum import Enum

from tanks.modes.win_condition import WinCondition


class MatchStatus(Enum):
    """Status of a tournament match."""

    PENDING = "pending"  # Not yet started
    IN_PROGRESS = "in_progress"  # Currently running
    COMPLETED = "completed"  # Match finished


@dataclass
class MatchResult:
    """Result of a completed match.

    Attributes:
        winner_indices: Indices of tanks that won (may be multiple for tie).
        loser_indices: Indices of tanks that lost.
        duration: Match duration in seconds.
        kill_counts: Final kill counts for each tank.
        damage_dealt: Total damage for each tank.

    """

    winner_indices: list[int]
    loser_indices: list[int]
    duration: float
    kill_counts: list[int] = field(default_factory=list)
    damage_dealt: list[float] = field(default_factory=list)

    def is_tie(self) -> bool:
        """Check if match ended in a tie.

        Returns:
            True if multiple winners or no clear winner.

        """
        return len(self.winner_indices) != 1 or len(self.winner_indices) == 0


@dataclass
class Match:
    """Represents a single tournament match.

    Attributes:
        match_id: Unique match identifier.
        tank_indices: Indices of participating tanks.
        map_config: Configuration for map generation.
        win_condition: Win condition for this match.
        status: Current match status.
        result: Result once match is completed.
        start_time: When match started (seconds since epoch).

    """

    match_id: str
    tank_indices: list[int]
    map_config: dict | None = None
    win_condition: WinCondition | None = None
    status: MatchStatus = MatchStatus.PENDING
    result: MatchResult | None = None
    start_time: float = 0.0

    def start(self, start_time: float = 0.0) -> None:
        """Mark match as started.

        Args:
            start_time: Epoch time when match starts.

        """
        self.status = MatchStatus.IN_PROGRESS
        self.start_time = start_time

    def complete(self, result: MatchResult) -> None:
        """Mark match as completed with result.

        Args:
            result: The match result.

        """
        self.status = MatchStatus.COMPLETED
        self.result = result

    def get_points(self, tank_index: int) -> int:
        """Get tournament points for a tank in this match.

        Points: Win=3, Tie=1, Loss=0

        Args:
            tank_index: Index of tank to check.

        Returns:
            Points earned in this match.

        """
        if not self.result or tank_index not in self.tank_indices:
            return 0

        if tank_index in self.result.winner_indices:
            if self.result.is_tie():
                return 1  # Tie
            return 3  # Win

        return 0  # Loss

    def get_summary(self) -> str:
        """Get human-readable match summary.

        Returns:
            Summary string.

        """
        if self.status == MatchStatus.PENDING:
            return f"Match {self.match_id}: Tanks {self.tank_indices} - PENDING"
        elif self.status == MatchStatus.IN_PROGRESS:
            return f"Match {self.match_id}: Tanks {self.tank_indices} - IN PROGRESS"
        elif self.status == MatchStatus.COMPLETED and self.result:
            winners = [
                self.tank_indices[i] if i < len(self.tank_indices) else i
                for i in self.result.winner_indices
            ]
            return f"Match {self.match_id}: Winners {winners} (Duration: {self.result.duration:.1f}s)"

        return f"Match {self.match_id}: Unknown"
