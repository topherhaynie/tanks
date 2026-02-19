"""Performance statistics tracking for tanks and bots."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


@dataclass
class TankStats:
    """Performance statistics for a single tank.

    Attributes:
        tank_id: Unique identifier for the tank.
        team: Team number.
        kills: Number of enemy tanks destroyed.
        deaths: Number of times this tank was destroyed (0 or 1).
        shots_fired: Total shots fired.
        shots_hit: Number of shots that hit a target.
        damage_dealt: Total damage dealt to enemies.
        damage_taken: Total damage received.
        survival_time: Total time alive in seconds.
        distance_traveled: Total distance traveled in pixels.

    """

    tank_id: int
    team: int
    kills: int = 0
    deaths: int = 0
    shots_fired: int = 0
    shots_hit: int = 0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    survival_time: float = 0.0
    distance_traveled: float = 0.0

    def accuracy(self) -> float:
        """Calculate shooting accuracy as a percentage.

        Returns:
            Accuracy percentage (0-100), or 0 if no shots fired.

        """
        if self.shots_fired == 0:
            return 0.0
        return (self.shots_hit / self.shots_fired) * 100.0

    def kd_ratio(self) -> float:
        """Calculate kill/death ratio.

        Returns:
            K/D ratio, or kills count if no deaths.

        """
        if self.deaths == 0:
            return float(self.kills)
        return self.kills / self.deaths

    def to_dict(self) -> dict:
        """Convert stats to dictionary format.

        Returns:
            Dictionary representation of stats.

        """
        return {
            "tank_id": self.tank_id,
            "team": self.team,
            "kills": self.kills,
            "deaths": self.deaths,
            "shots_fired": self.shots_fired,
            "shots_hit": self.shots_hit,
            "accuracy": round(self.accuracy(), 2),
            "damage_dealt": round(self.damage_dealt, 1),
            "damage_taken": round(self.damage_taken, 1),
            "survival_time": round(self.survival_time, 2),
            "distance_traveled": round(self.distance_traveled, 1),
            "kd_ratio": round(self.kd_ratio(), 2),
        }


class StatsTracker:
    """Tracks performance statistics for all tanks in a match.

    Maintains per-tank statistics and provides aggregation and reporting.

    Attributes:
        stats: Dictionary mapping tank ID to TankStats.
        match_start_time: Time when tracking started.

    """

    def __init__(self) -> None:
        """Initialize the stats tracker."""
        self.stats: dict[int, TankStats] = {}
        self.match_start_time: float = 0.0
        self._last_positions: dict[int, tuple[float, float]] = {}

    def register_tank(self, tank: "Tank") -> None:
        """Register a tank for stats tracking.

        Args:
            tank: Tank entity to track.

        """
        if tank.id not in self.stats:
            self.stats[tank.id] = TankStats(tank_id=tank.id, team=tank.team)
            self._last_positions[tank.id] = (tank.x, tank.y)

    def record_shot(self, tank: "Tank") -> None:
        """Record a shot fired by a tank.

        Args:
            tank: Tank that fired the shot.

        """
        if tank.id in self.stats:
            self.stats[tank.id].shots_fired += 1

    def record_hit(
        self, shooter_tank: "Tank", target_tank: "Tank", damage: float
    ) -> None:
        """Record a successful hit on a target.

        Args:
            shooter_tank: Tank that fired the shot.
            target_tank: Tank that was hit.
            damage: Damage dealt.

        """
        if shooter_tank.id in self.stats:
            self.stats[shooter_tank.id].shots_hit += 1
            self.stats[shooter_tank.id].damage_dealt += damage

        if target_tank.id in self.stats:
            self.stats[target_tank.id].damage_taken += damage

    def record_kill(self, killer_tank: "Tank", victim_tank: "Tank") -> None:
        """Record a kill when a tank destroys another.

        Args:
            killer_tank: Tank that got the kill.
            victim_tank: Tank that was destroyed.

        """
        if killer_tank.id in self.stats:
            self.stats[killer_tank.id].kills += 1

        if victim_tank.id in self.stats:
            self.stats[victim_tank.id].deaths += 1

    def update_survival_time(self, tank: "Tank", dt: float) -> None:
        """Update survival time for an active tank.

        Args:
            tank: Tank to update.
            dt: Time delta in seconds.

        """
        if tank.id in self.stats and tank.active:
            self.stats[tank.id].survival_time += dt

    def update_distance(self, tank: "Tank") -> None:
        """Update distance traveled for a tank.

        Args:
            tank: Tank to update.

        """
        if tank.id not in self.stats or tank.id not in self._last_positions:
            return

        last_x, last_y = self._last_positions[tank.id]
        dx = tank.x - last_x
        dy = tank.y - last_y
        distance = (dx**2 + dy**2) ** 0.5

        self.stats[tank.id].distance_traveled += distance
        self._last_positions[tank.id] = (tank.x, tank.y)

    def get_stats(self, tank_id: int) -> TankStats | None:
        """Get stats for a specific tank.

        Args:
            tank_id: ID of the tank.

        Returns:
            TankStats for the tank, or None if not found.

        """
        return self.stats.get(tank_id)

    def get_all_stats(self) -> list[TankStats]:
        """Get stats for all tracked tanks.

        Returns:
            List of TankStats for all tanks.

        """
        return list(self.stats.values())

    def get_leaderboard(self, sort_by: str = "kills") -> list[TankStats]:
        """Get sorted leaderboard of tank performance.

        Args:
            sort_by: Stat to sort by (kills, accuracy, damage_dealt, kd_ratio).

        Returns:
            Sorted list of TankStats.

        """
        stats_list = self.get_all_stats()

        if sort_by == "kills":
            return sorted(stats_list, key=lambda s: s.kills, reverse=True)
        if sort_by == "accuracy":
            return sorted(stats_list, key=lambda s: s.accuracy(), reverse=True)
        if sort_by == "damage_dealt":
            return sorted(stats_list, key=lambda s: s.damage_dealt, reverse=True)
        if sort_by == "kd_ratio":
            return sorted(stats_list, key=lambda s: s.kd_ratio(), reverse=True)
        return stats_list

    def get_team_stats(self, team: int) -> dict:
        """Get aggregated stats for a team.

        Args:
            team: Team number.

        Returns:
            Dictionary with aggregated team stats.

        """
        team_tanks = [s for s in self.stats.values() if s.team == team]

        if not team_tanks:
            return {}

        return {
            "team": team,
            "total_kills": sum(s.kills for s in team_tanks),
            "total_deaths": sum(s.deaths for s in team_tanks),
            "total_damage_dealt": sum(s.damage_dealt for s in team_tanks),
            "avg_accuracy": sum(s.accuracy() for s in team_tanks) / len(team_tanks),
            "total_shots_fired": sum(s.shots_fired for s in team_tanks),
            "total_shots_hit": sum(s.shots_hit for s in team_tanks),
        }

    def reset(self) -> None:
        """Reset all statistics."""
        self.stats.clear()
        self._last_positions.clear()
        self.match_start_time = 0.0

    def print_summary(self) -> None:
        """Print a formatted summary of all statistics."""
        print("\n" + "=" * 80)  # noqa: T201
        print("MATCH STATISTICS")  # noqa: T201
        print("=" * 80)  # noqa: T201

        for stats in self.get_leaderboard("kills"):
            print(f"\nTank {stats.tank_id} (Team {stats.team}):")  # noqa: T201
            print(
                f"  Kills: {stats.kills}  Deaths: {stats.deaths}  K/D: {stats.kd_ratio():.2f}"
            )  # noqa: T201
            print(  # noqa: T201
                f"  Accuracy: {stats.accuracy():.1f}% ({stats.shots_hit}/{stats.shots_fired} shots)",
            )
            print(  # noqa: T201
                f"  Damage: {stats.damage_dealt:.0f} dealt, {stats.damage_taken:.0f} taken",
            )
            print(f"  Survival: {stats.survival_time:.1f}s")  # noqa: T201
            print(f"  Distance: {stats.distance_traveled:.0f}px")  # noqa: T201

        print("\n" + "=" * 80)  # noqa: T201
