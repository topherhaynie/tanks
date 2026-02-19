"""ELO rating system for agents and bots.

Implements ELO ranking system to track relative skill levels of agents and bots.
Useful for matchmaking and measuring training progress.
"""

import json
import math
from pathlib import Path
from typing import Any


class ELORatingSystem:
    """ELO rating system for agents.

    Tracks ratings for multiple agents/bots and updates after matches.
    Standard starting rating is 1500 with K-factor of 32.

    Args:
        k_factor: Rating change multiplier. Default: 32 (standard).
        starting_rating: Initial rating for new players. Default: 1500.
        storage_path: Optional path to persist ratings. Default: None.

    """

    def __init__(
        self,
        k_factor: int = 32,
        starting_rating: int = 1500,
        storage_path: str | None = None,
    ) -> None:
        """Initialize ELO rating system."""
        self.k_factor = k_factor
        self.starting_rating = starting_rating
        self.storage_path = Path(storage_path) if storage_path else None

        # Rating storage: player_id -> rating
        self.ratings: dict[str, float] = {}

        # Match history: for statistics
        self.match_count: dict[str, int] = {}
        self.win_count: dict[str, int] = {}

        # Load existing ratings if available
        if self.storage_path and self.storage_path.exists():
            self.load()

    def get_rating(self, player_id: str) -> float:
        """Get current rating for a player.

        Args:
            player_id: Unique player identifier.

        Returns:
            Current ELO rating.

        """
        if player_id not in self.ratings:
            self.ratings[player_id] = float(self.starting_rating)
            self.match_count[player_id] = 0
            self.win_count[player_id] = 0

        return self.ratings[player_id]

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for player A vs player B.

        Args:
            rating_a: Player A's rating.
            rating_b: Player B's rating.

        Returns:
            Expected score (probability of winning) for player A.

        """
        return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))

    def update_ratings(
        self,
        player_a_id: str,
        player_b_id: str,
        score_a: float,
    ) -> tuple[float, float]:
        """Update ratings after a match.

        Args:
            player_a_id: Player A identifier.
            player_b_id: Player B identifier.
            score_a: Actual score for player A (1.0 = win, 0.5 = draw, 0.0 = loss).

        Returns:
            Tuple of (new_rating_a, new_rating_b).

        """
        # Get current ratings
        rating_a = self.get_rating(player_a_id)
        rating_b = self.get_rating(player_b_id)

        # Calculate expected scores
        expected_a = self.expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        # Calculate score for player B
        score_b = 1.0 - score_a

        # Update ratings
        new_rating_a = rating_a + self.k_factor * (score_a - expected_a)
        new_rating_b = rating_b + self.k_factor * (score_b - expected_b)

        # Store new ratings
        self.ratings[player_a_id] = new_rating_a
        self.ratings[player_b_id] = new_rating_b

        # Update match statistics
        self.match_count[player_a_id] = self.match_count.get(player_a_id, 0) + 1
        self.match_count[player_b_id] = self.match_count.get(player_b_id, 0) + 1

        if score_a > 0.5:
            self.win_count[player_a_id] = self.win_count.get(player_a_id, 0) + 1
        elif score_b > 0.5:
            self.win_count[player_b_id] = self.win_count.get(player_b_id, 0) + 1

        # Save if storage enabled
        if self.storage_path:
            self.save()

        return new_rating_a, new_rating_b

    def record_match(
        self,
        winner_id: str,
        loser_id: str,
        draw: bool = False,
    ) -> tuple[float, float]:
        """Record a match result and update ratings.

        Args:
            winner_id: Winner's player ID.
            loser_id: Loser's player ID.
            draw: Whether the match was a draw. Default: False.

        Returns:
            Tuple of (winner_new_rating, loser_new_rating).

        """
        if draw:
            return self.update_ratings(winner_id, loser_id, 0.5)
        return self.update_ratings(winner_id, loser_id, 1.0)

    def get_leaderboard(self, limit: int | None = None) -> list[tuple[str, float, int, float]]:
        """Get leaderboard sorted by rating.

        Args:
            limit: Maximum number of entries to return. Default: None (all).

        Returns:
            List of (player_id, rating, matches, win_rate) tuples.

        """
        leaderboard = []

        for player_id, rating in self.ratings.items():
            matches = self.match_count.get(player_id, 0)
            wins = self.win_count.get(player_id, 0)
            win_rate = wins / matches if matches > 0 else 0.0

            leaderboard.append((player_id, rating, matches, win_rate))

        # Sort by rating (descending)
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        if limit is not None:
            leaderboard = leaderboard[:limit]

        return leaderboard

    def print_leaderboard(self, limit: int = 10) -> None:
        """Print leaderboard to console.

        Args:
            limit: Maximum entries to display. Default: 10.

        """
        leaderboard = self.get_leaderboard(limit)

        print(f"\n{'=' * 70}")
        print(f"{'ELO Leaderboard':^70}")
        print(f"{'=' * 70}")
        print(f"{'Rank':<6} {'Player':<25} {'Rating':<10} {'Matches':<10} {'Win Rate':<10}")
        print(f"{'-' * 70}")

        for rank, (player_id, rating, matches, win_rate) in enumerate(leaderboard, 1):
            print(
                f"{rank:<6} {player_id:<25} {rating:<10.0f} {matches:<10} {win_rate:<10.1%}",
            )

        print(f"{'=' * 70}\n")

    def get_stats(self, player_id: str) -> dict[str, Any]:
        """Get statistics for a player.

        Args:
            player_id: Player identifier.

        Returns:
            Dictionary with rating, matches, wins, win_rate.

        """
        rating = self.get_rating(player_id)
        matches = self.match_count.get(player_id, 0)
        wins = self.win_count.get(player_id, 0)
        win_rate = wins / matches if matches > 0 else 0.0

        return {
            "player_id": player_id,
            "rating": rating,
            "matches": matches,
            "wins": wins,
            "win_rate": win_rate,
        }

    def reset_player(self, player_id: str) -> None:
        """Reset a player's rating to starting rating.

        Args:
            player_id: Player identifier.

        """
        if player_id in self.ratings:
            self.ratings[player_id] = float(self.starting_rating)
            self.match_count[player_id] = 0
            self.win_count[player_id] = 0

            if self.storage_path:
                self.save()

    def save(self) -> None:
        """Save ratings to disk."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "k_factor": self.k_factor,
            "starting_rating": self.starting_rating,
            "ratings": self.ratings,
            "match_count": self.match_count,
            "win_count": self.win_count,
        }

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        """Load ratings from disk."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path) as f:
                data = json.load(f)

            self.k_factor = data.get("k_factor", self.k_factor)
            self.starting_rating = data.get("starting_rating", self.starting_rating)
            self.ratings = data.get("ratings", {})
            self.match_count = data.get("match_count", {})
            self.win_count = data.get("win_count", {})

            print(f"Loaded ELO ratings for {len(self.ratings)} players from {self.storage_path}")
        except Exception as e:
            print(f"Failed to load ELO ratings: {e}")


def create_default_elo_system(storage_dir: str = "checkpoints/elo") -> ELORatingSystem:
    """Create default ELO rating system with persistent storage.

    Args:
        storage_dir: Directory to store ratings. Default: "checkpoints/elo".

    Returns:
        Configured ELO rating system.

    """
    Path(storage_dir).mkdir(parents=True, exist_ok=True)
    storage_path = Path(storage_dir) / "ratings.json"

    return ELORatingSystem(
        k_factor=32,
        starting_rating=1500,
        storage_path=str(storage_path),
    )
