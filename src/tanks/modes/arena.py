"""Arena mode for multi-tank battles."""

from dataclasses import dataclass, field
from enum import Enum

from tanks.maps import MapSize, TerrainPattern
from tanks.modes.win_condition import WinCondition, WinConditionType


class ArenaSize(Enum):
    """Arena difficulty levels with player counts."""

    SKIRMISH = (3, "3-4 tanks")  # 3-4 tanks, smaller map
    STANDARD = (4, "4 tanks")  # 4 tanks, medium map
    LARGE = (6, "6 tanks")  # 6 tanks, large map
    CHAOS = (8, "8 tanks")  # 8 tanks, huge map

    def __init__(self, tank_count: int, label: str) -> None:
        """Initialize arena size.

        Args:
            tank_count: Number of tanks in arena.
            label: Human-readable label.

        """
        self.tank_count = tank_count
        self.label = label


@dataclass
class ArenaConfig:
    """Configuration for an arena battle.

    Attributes:
        name: Arena name.
        arena_size: Number of tanks participating.
        map_size: Size of generated map.
        terrain_pattern: Type of terrain generation.
        bot_types: List of bot types (mix of "simple", "smart", "cpp").
        win_condition: How the match ends.
        seed: Random seed for map generation (None = random).

    """

    name: str = "Arena Battle"
    arena_size: ArenaSize = ArenaSize.STANDARD
    map_size: MapSize = MapSize.MEDIUM
    terrain_pattern: TerrainPattern = TerrainPattern.SCATTERED
    bot_types: list[str] = field(default_factory=lambda: ["simple", "smart", "smart"])
    win_condition: WinCondition = field(
        default_factory=lambda: WinCondition(WinConditionType.LAST_ALIVE)
    )
    seed: int | None = None

    def get_tank_count(self) -> int:
        """Get total number of tanks.

        Returns:
            Number of tanks in arena.

        """
        return self.arena_size.tank_count

    def get_description(self) -> str:
        """Get human-readable arena description.

        Returns:
            Description string.

        """
        return f"{self.name} ({self.arena_size.label}, {self.terrain_pattern.value})"


@dataclass
class ArenaStats:
    """Statistics for an arena battle.

    Attributes:
        total_time: Total duration of arena (seconds).
        tanks_played: Number of tanks that participated.
        winner_index: Index of winning tank (or -1 for tie).
        kill_counts: Kill count for each tank.
        death_counts: Death count for each tank.
        damage_dealt: Total damage for each tank.

    """

    total_time: float = 0.0
    tanks_played: int = 0
    winner_index: int = -1
    kill_counts: list[int] = field(default_factory=list)
    death_counts: list[int] = field(default_factory=list)
    damage_dealt: list[float] = field(default_factory=list)

    def get_leader(self) -> tuple[int, str]:
        """Get the tank with most kills.

        Returns:
            Tuple of (tank_index, stat_label).

        """
        if not self.kill_counts:
            return -1, "No tanks"

        max_kills = max(self.kill_counts)
        leader = self.kill_counts.index(max_kills)
        return leader, f"{max_kills} kills"

    def get_summary(self) -> str:
        """Get arena stats summary.

        Returns:
            Summary string.

        """
        if self.winner_index >= 0:
            return f"Arena completed in {self.total_time:.1f}s - Tank {self.winner_index} won"
        return f"Arena in progress ({self.total_time:.1f}s elapsed)"
