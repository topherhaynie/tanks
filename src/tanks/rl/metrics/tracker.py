"""Metrics tracking for RL training.

This module provides comprehensive metrics collection for training episodes,
including rewards, combat stats, exploration, and learning progress.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    pass


@dataclass
class TrainingMetrics:
    """Metrics for a single training episode.
    
    Attributes:
        episode: Episode number.
        reward: Total episode reward.
        length: Number of steps in episode.
        loss: Average training loss (if trained).
        epsilon: Exploration rate.
        won: Whether agent won the episode.
        kills: Number of enemy kills.
        deaths: Number of deaths (0 or 1).
        damage_dealt: Total damage dealt to enemies.
        damage_taken: Total damage received.
        shots_fired: Number of shots fired.
        shots_hit: Number of shots that hit enemies.
        survival_time: Steps survived before death.
        q_value_mean: Average Q-value across actions.
        q_value_max: Maximum Q-value seen.
        actions_taken: Count of each action taken (dict).
        terrain_revealed: Fog tiles revealed this episode.
    """
    
    episode: int
    reward: float
    length: int
    loss: float = 0.0
    epsilon: float = 1.0
    won: bool = False
    kills: int = 0
    deaths: int = 0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    shots_fired: int = 0
    shots_hit: int = 0
    survival_time: int = 0
    q_value_mean: float = 0.0
    q_value_max: float = 0.0
    actions_taken: dict[int, int] = field(default_factory=dict)
    terrain_revealed: int = 0
    
    @property
    def win_rate(self) -> float:
        """Win rate (1.0 if won, 0.0 if lost)."""
        return 1.0 if self.won else 0.0
    
    @property
    def accuracy(self) -> float:
        """Shooting accuracy (hits / shots)."""
        if self.shots_fired == 0:
            return 0.0
        return self.shots_hit / self.shots_fired
    
    @property
    def kd_ratio(self) -> float:
        """Kill/Death ratio."""
        if self.deaths == 0:
            return float(self.kills)
        return self.kills / self.deaths
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "episode": self.episode,
            "reward": self.reward,
            "length": self.length,
            "loss": self.loss,
            "epsilon": self.epsilon,
            "won": self.won,
            "win_rate": self.win_rate,
            "kills": self.kills,
            "deaths": self.deaths,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "shots_fired": self.shots_fired,
            "shots_hit": self.shots_hit,
            "accuracy": self.accuracy,
            "kd_ratio": self.kd_ratio,
            "survival_time": self.survival_time,
            "q_value_mean": self.q_value_mean,
            "q_value_max": self.q_value_max,
            "terrain_revealed": self.terrain_revealed,
        }


class MetricsTracker:
    """Tracks and aggregates training metrics over time.
    
    Provides rolling averages, statistics, and export functionality.
    
    Args:
        window_size: Size of rolling window for averages. Default: 100.
        save_dir: Directory to save metrics CSV. Default: None (no save).
    """
    
    def __init__(
        self,
        window_size: int = 100,
        save_dir: str | None = None,
    ) -> None:
        """Initialize metrics tracker."""
        self.window_size = window_size
        self.save_dir = Path(save_dir) if save_dir else None
        
        # Storage
        self.metrics_history: list[TrainingMetrics] = []
        
        # Running totals
        self.total_episodes = 0
        self.total_steps = 0
        self.total_wins = 0
        
        # Create save directory
        if self.save_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def add(self, metrics: TrainingMetrics) -> None:
        """Add episode metrics.
        
        Args:
            metrics: Metrics from completed episode.
        """
        self.metrics_history.append(metrics)
        
        # Update totals
        self.total_episodes += 1
        self.total_steps += metrics.length
        if metrics.won:
            self.total_wins += 1
    
    def get_recent(self, n: int | None = None) -> list[TrainingMetrics]:
        """Get recent metrics.
        
        Args:
            n: Number of recent episodes. Uses window_size if None.
        
        Returns:
            List of recent metrics.
        """
        n = n or self.window_size
        return self.metrics_history[-n:]
    
    def get_rolling_avg(self, key: str, window: int | None = None) -> float:
        """Get rolling average of a metric.
        
        Args:
            key: Metric name (e.g., 'reward', 'win_rate', 'accuracy').
            window: Window size. Uses tracker window_size if None.
        
        Returns:
            Rolling average value.
        """
        window = window or self.window_size
        recent = self.get_recent(window)
        
        if not recent:
            return 0.0
        
        # Get values
        if key == "win_rate":
            values = [m.win_rate for m in recent]
        elif key == "accuracy":
            values = [m.accuracy for m in recent]
        elif key == "kd_ratio":
            values = [m.kd_ratio for m in recent]
        else:
            values = [getattr(m, key, 0.0) for m in recent]
        
        return float(np.mean(values))
    
    def get_stats(self, window: int | None = None) -> dict[str, float]:
        """Get statistics for recent episodes.
        
        Args:
            window: Window size for stats. Default: window_size.
        
        Returns:
            Dictionary of statistics.
        """
        recent = self.get_recent(window)
        
        if not recent:
            return {}
        
        return {
            "episodes": len(recent),
            "mean_reward": float(np.mean([m.reward for m in recent])),
            "std_reward": float(np.std([m.reward for m in recent])),
            "mean_length": float(np.mean([m.length for m in recent])),
            "win_rate": float(np.mean([m.win_rate for m in recent])),
            "mean_loss": float(np.mean([m.loss for m in recent if m.loss > 0])),
            "mean_accuracy": float(np.mean([m.accuracy for m in recent])),
            "mean_kd": float(np.mean([m.kd_ratio for m in recent])),
            "mean_q_value": float(np.mean([m.q_value_mean for m in recent])),
            "total_wins": int(sum(m.won for m in recent)),
            "total_kills": int(sum(m.kills for m in recent)),
            "total_deaths": int(sum(m.deaths for m in recent)),
        }
    
    def print_summary(self, window: int | None = None) -> None:
        """Print training summary.
        
        Args:
            window: Window for recent stats. Default: window_size.
        """
        stats = self.get_stats(window)
        
        if not stats:
            print("No metrics recorded yet.")
            return
        
        print(f"\n{'=' * 60}")
        print(f"Training Summary (last {stats['episodes']} episodes)")
        print(f"{'=' * 60}")
        print(f"Total Episodes: {self.total_episodes}")
        print(f"Total Steps: {self.total_steps}")
        print(f"Overall Win Rate: {self.total_wins / max(self.total_episodes, 1):.1%}")
        print()
        print("Recent Performance:")
        print(f"  Reward: {stats['mean_reward']:+.2f} ± {stats['std_reward']:.2f}")
        print(f"  Length: {stats['mean_length']:.0f} steps")
        print(f"  Win Rate: {stats['win_rate']:.1%} ({stats['total_wins']}/{stats['episodes']})")
        print(f"  Kills/Deaths: {stats['total_kills']}/{stats['total_deaths']}")
        print(f"  K/D Ratio: {stats['mean_kd']:.2f}")
        print(f"  Accuracy: {stats['mean_accuracy']:.1%}")
        print(f"  Avg Loss: {stats['mean_loss']:.4f}")
        print(f"  Avg Q-Value: {stats['mean_q_value']:.2f}")
        print(f"{'=' * 60}\n")
    
    def save_csv(self, filename: str = "training_metrics.csv") -> None:
        """Save metrics to CSV file.
        
        Args:
            filename: Output filename.
        """
        if not self.save_dir:
            error_msg = "No save directory configured"
            raise ValueError(error_msg)
        
        import csv
        
        filepath = self.save_dir / filename
        
        # Write CSV
        with filepath.open("w", newline="") as f:
            if not self.metrics_history:
                return
            
            writer = csv.DictWriter(f, fieldnames=self.metrics_history[0].to_dict().keys())
            writer.writeheader()
            
            for metrics in self.metrics_history:
                writer.writerow(metrics.to_dict())
        
        print(f"Metrics saved to: {filepath}")
    
    def get_action_distribution(self, window: int | None = None) -> dict[int, int]:
        """Get action distribution over recent episodes.
        
        Args:
            window: Window size. Default: window_size.
        
        Returns:
            Dictionary mapping action_id -> count.
        """
        recent = self.get_recent(window)
        
        distribution: dict[int, int] = {}
        for metrics in recent:
            for action_id, count in metrics.actions_taken.items():
                distribution[action_id] = distribution.get(action_id, 0) + count
        
        return distribution
