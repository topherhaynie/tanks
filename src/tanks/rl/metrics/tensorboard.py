"""TensorBoard integration for training visualization.

This module provides TensorBoard logging for real-time monitoring of
training progress, including scalars, histograms, and custom visualizations.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.rl.metrics.tracker import TrainingMetrics


class TensorBoardLogger:
    """TensorBoard logger for training metrics.
    
    Logs scalars, histograms, and other metrics to TensorBoard for
    real-time visualization during training.
    
    Args:
        log_dir: Directory for TensorBoard logs.
        enabled: Whether logging is enabled. Default: True.
    
    Example:
        ```python
        logger = TensorBoardLogger("runs/dqn_training")
        
        for episode in range(1000):
            # Train...
            logger.log_episode(metrics, episode)
        
        logger.close()
        ```
    
    To view logs:
        ```bash
        tensorboard --logdir runs/
        ```
    """
    
    def __init__(
        self,
        log_dir: str,
        enabled: bool = True,
    ) -> None:
        """Initialize TensorBoard logger."""
        self.log_dir = Path(log_dir)
        self.enabled = enabled
        self.writer = None
        
        if self.enabled:
            try:
                from torch.utils.tensorboard import SummaryWriter
                
                self.log_dir.mkdir(parents=True, exist_ok=True)
                self.writer = SummaryWriter(str(self.log_dir))
                print(f"TensorBoard logging to: {self.log_dir}")
                print(f"  View with: tensorboard --logdir {self.log_dir.parent}")
            except ImportError:
                print("Warning: tensorboard not installed. Logging disabled.")
                print("  Install with: pip install tensorboard")
                self.enabled = False
    
    def log_scalar(self, tag: str, value: float, step: int) -> None:
        """Log scalar value.
        
        Args:
            tag: Metric name (e.g., 'reward', 'loss').
            value: Scalar value.
            step: Training step/episode number.
        """
        if self.enabled and self.writer:
            self.writer.add_scalar(tag, value, step)
    
    def log_scalars(self, tag: str, values: dict[str, float], step: int) -> None:
        """Log multiple scalar values with same tag.
        
        Args:
            tag: Group name (e.g., 'combat').
            values: Dictionary of metric_name -> value.
            step: Training step/episode number.
        """
        if self.enabled and self.writer:
            self.writer.add_scalars(tag, values, step)
    
    def log_histogram(self, tag: str, values: list[float], step: int) -> None:
        """Log histogram of values.
        
        Args:
            tag: Histogram name (e.g., 'q_values').
            values: List of values to histogram.
            step: Training step/episode number.
        """
        if self.enabled and self.writer:
            import torch
            self.writer.add_histogram(tag, torch.FloatTensor(values), step)
    
    def log_episode(self, metrics: "TrainingMetrics", episode: int) -> None:
        """Log all metrics from an episode.
        
        Args:
            metrics: Episode metrics.
            episode: Episode number.
        """
        if not self.enabled or not self.writer:
            return
        
        # Episode metrics
        self.log_scalar("episode/reward", metrics.reward, episode)
        self.log_scalar("episode/length", metrics.length, episode)
        self.log_scalar("episode/win_rate", metrics.win_rate, episode)
        
        # Training metrics
        if metrics.loss > 0:
            self.log_scalar("training/loss", metrics.loss, episode)
        self.log_scalar("training/epsilon", metrics.epsilon, episode)
        self.log_scalar("training/q_value_mean", metrics.q_value_mean, episode)
        self.log_scalar("training/q_value_max", metrics.q_value_max, episode)
        
        # Combat metrics
        self.log_scalars("combat", {
            "kills": float(metrics.kills),
            "deaths": float(metrics.deaths),
            "damage_dealt": metrics.damage_dealt,
            "damage_taken": metrics.damage_taken,
        }, episode)
        
        # Accuracy metrics
        self.log_scalar("accuracy/shooting", metrics.accuracy, episode)
        self.log_scalar("accuracy/kd_ratio", metrics.kd_ratio, episode)
        
        # Survival
        self.log_scalar("survival/time", metrics.survival_time, episode)
        
        # Exploration
        self.log_scalar("exploration/terrain_revealed", metrics.terrain_revealed, episode)
        
        # Action distribution (as histogram)
        if metrics.actions_taken:
            action_list = []
            for action_id, count in metrics.actions_taken.items():
                action_list.extend([action_id] * count)
            if action_list:
                self.log_histogram("actions/distribution", action_list, episode)
    
    def log_evaluation(
        self,
        eval_metrics: dict[str, float],
        episode: int,
    ) -> None:
        """Log evaluation results.
        
        Args:
            eval_metrics: Dictionary of evaluation metrics.
            episode: Current training episode.
        """
        if not self.enabled or not self.writer:
            return
        
        for key, value in eval_metrics.items():
            self.log_scalar(f"eval/{key}", value, episode)
    
    def flush(self) -> None:
        """Flush pending writes to disk."""
        if self.enabled and self.writer:
            self.writer.flush()
    
    def close(self) -> None:
        """Close logger and flush writes."""
        if self.enabled and self.writer:
            self.writer.close()
            print(f"TensorBoard logs saved to: {self.log_dir}")
