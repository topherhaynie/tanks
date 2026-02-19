"""Tournament orchestration and leaderboard system."""

from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations

from tanks.modes.match import Match, MatchResult, MatchStatus
from tanks.modes.win_condition import WinCondition, WinConditionType


class TournamentFormat(Enum):
    """Tournament formats."""

    ROUND_ROBIN = "round_robin"  # Every tank plays every other tank
    ELIMINATION = "elimination"  # Single or double elimination
    LADDER = "ladder"  # Ranking-based progressive matches


@dataclass
class TankRanking:
    """A tank's ranking in the tournament.

    Attributes:
        tank_index: Index of the tank.
        tank_name: Name of the tank.
        wins: Number of matches won.
        losses: Number of matches lost.
        ties: Number of matches tied.
        points: Total tournament points (Win=3, Tie=1).
        kills: Total kills across all matches.
        deaths: Total deaths across all matches.

    """

    tank_index: int
    tank_name: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points: int = 0
    kills: int = 0
    deaths: int = 0

    @property
    def total_matches(self) -> int:
        """Total matches played.

        Returns:
            Number of matches completed.

        """
        return self.wins + self.losses + self.ties

    @property
    def kill_death_ratio(self) -> float:
        """Kill to death ratio.

        Returns:
            K/D ratio (or 0 if no deaths).

        """
        if self.deaths == 0:
            return float(self.kills) if self.kills > 0 else 0.0
        return self.kills / self.deaths

    def __lt__(self, other: "TankRanking") -> bool:
        """Compare rankings (for sorting).

        Sorts by: points (desc), K/D ratio (desc), kills (desc).

        Args:
            other: Other ranking to compare to.

        Returns:
            True if self ranks lower than other.

        """
        if self.points != other.points:
            return self.points > other.points
        if self.kill_death_ratio != other.kill_death_ratio:
            return self.kill_death_ratio > other.kill_death_ratio
        return self.kills > other.kills


@dataclass
class Tournament:
    """Tournament managing multiple matches and rankings.

    Attributes:
        name: Tournament name.
        format: Tournament format.
        tank_names: List of tank names participating.
        win_condition: Win condition for each match.
        matches: Completed and pending matches.
        current_match_index: Index of currently playing match (or -1 if none).

    """

    name: str
    format: TournamentFormat
    tank_names: list[str]
    win_condition: WinCondition = field(
        default_factory=lambda: WinCondition(WinConditionType.LAST_ALIVE)
    )
    matches: list[Match] = field(default_factory=list)
    current_match_index: int = -1

    def __post_init__(self) -> None:
        """Generate matches based on tournament format."""
        if not self.matches:
            self._generate_matches()

    def _generate_matches(self) -> None:
        """Generate match schedule based on format."""
        if self.format == TournamentFormat.ROUND_ROBIN:
            self._generate_round_robin()
        elif self.format == TournamentFormat.ELIMINATION:
            self._generate_elimination()
        elif self.format == TournamentFormat.LADDER:
            self._generate_ladder()

    def _generate_round_robin(self) -> None:
        """Generate round-robin schedule - every tank plays every other tank."""
        tank_indices = list(range(len(self.tank_names)))
        match_id = 0

        for tank_a, tank_b in combinations(tank_indices, 2):
            match = Match(
                match_id=f"RR_{match_id}",
                tank_indices=[tank_a, tank_b],
                win_condition=WinCondition(
                    type=self.win_condition.type,
                    time_limit_seconds=self.win_condition.time_limit_seconds,
                    target_kills=self.win_condition.target_kills,
                ),
            )
            self.matches.append(match)
            match_id += 1

    def _generate_elimination(self) -> None:
        """Generate single elimination bracket."""
        tank_indices = list(range(len(self.tank_names)))

        # For now, just linear pairing (not full bracket)
        match_id = 0
        for i in range(0, len(tank_indices) - 1, 2):
            match = Match(
                match_id=f"SE_{match_id}",
                tank_indices=[tank_indices[i], tank_indices[i + 1]],
                win_condition=WinCondition(
                    type=self.win_condition.type,
                    time_limit_seconds=self.win_condition.time_limit_seconds,
                    target_kills=self.win_condition.target_kills,
                ),
            )
            self.matches.append(match)
            match_id += 1

    def _generate_ladder(self) -> None:
        """Generate ladder-style matches - ranked tank plays next ranked tank."""
        tank_indices = list(range(len(self.tank_names)))

        # Initial seeding matches
        match_id = 0
        for i in range(0, len(tank_indices) - 1, 2):
            match = Match(
                match_id=f"SEED_{match_id}",
                tank_indices=[tank_indices[i], tank_indices[i + 1]],
                win_condition=WinCondition(
                    type=self.win_condition.type,
                    time_limit_seconds=self.win_condition.time_limit_seconds,
                    target_kills=self.win_condition.target_kills,
                ),
            )
            self.matches.append(match)
            match_id += 1

    def get_next_match(self) -> Match | None:
        """Get the next pending match to play.

        Returns:
            Next Match to play, or None if all complete.

        """
        for i, match in enumerate(self.matches):
            if match.status == MatchStatus.PENDING:
                self.current_match_index = i
                return match

        return None

    def get_current_match(self) -> Match | None:
        """Get the currently playing match.

        Returns:
            Current Match or None.

        """
        if 0 <= self.current_match_index < len(self.matches):
            return self.matches[self.current_match_index]
        return None

    def complete_current_match(self, result: MatchResult) -> None:
        """Mark current match as completed.

        Args:
            result: The match result.

        """
        if 0 <= self.current_match_index < len(self.matches):
            match = self.matches[self.current_match_index]
            match.complete(result)

    def get_standings(self) -> list[TankRanking]:
        """Get current tournament standings.

        Returns:
            List of TankRanking sorted by points/record.

        """
        rankings = [
            TankRanking(tank_index=i, tank_name=self.tank_names[i])
            for i in range(len(self.tank_names))
        ]

        # Accumulate results from completed matches
        for match in self.matches:
            if match.status == MatchStatus.COMPLETED and match.result:
                result = match.result

                for i, tank_idx in enumerate(match.tank_indices):
                    ranking = rankings[tank_idx]
                    points = match.get_points(i)

                    if i in result.winner_indices:
                        if result.is_tie():
                            ranking.ties += 1
                        else:
                            ranking.wins += 1
                    else:
                        ranking.losses += 1

                    ranking.points += points
                    if i < len(result.kill_counts):
                        ranking.kills += result.kill_counts[i]
                    if i < len(result.damage_dealt):
                        ranking.deaths += 1  # Simplified - would be actual deaths

        # Sort by standings
        rankings.sort()
        return rankings

    def get_progress(self) -> tuple[int, int]:
        """Get tournament progress.

        Returns:
            Tuple of (completed_matches, total_matches).

        """
        completed = sum(1 for m in self.matches if m.status == MatchStatus.COMPLETED)
        return completed, len(self.matches)

    def is_complete(self) -> bool:
        """Check if tournament is finished.

        Returns:
            True if all matches completed.

        """
        return all(m.status == MatchStatus.COMPLETED for m in self.matches)

    def get_summary(self) -> str:
        """Get tournament summary.

        Returns:
            Summary string.

        """
        completed, total = self.get_progress()
        return f"{self.name} - {self.format.value} ({completed}/{total} matches)"
