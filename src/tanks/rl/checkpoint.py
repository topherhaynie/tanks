"""Checkpoint management for RL training.

This module provides checkpoint saving, loading, and opponent pool management
for self-play training.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tanks.rl.models.agent import Agent


class CheckpointManager:
    """Manages training checkpoints and opponent pools.
    
    Handles periodic checkpoint saves, best model tracking, and opponent
    pool management for self-play training.
    
    Directory structure:
        checkpoint_dir/
        ├── config.json          # Training configuration
        ├── best_model.pt        # Best performing model
        ├── latest_model.pt      # Most recent model
        ├── checkpoints/         # Periodic snapshots
        │   ├── episode_1000.pt
        │   ├── episode_2000.pt
        │   └── ...
        └── opponents/           # Self-play opponent pool
            ├── opponent_v1.pt
            ├── opponent_v2.pt
            └── ...
    
    Args:
        checkpoint_dir: Root directory for checkpoints.
        max_checkpoints: Maximum periodic checkpoints to keep. Default: 10.
        max_opponents: Maximum opponents in pool. Default: 10.
    """
    
    def __init__(
        self,
        checkpoint_dir: str,
        max_checkpoints: int = 10,
        max_opponents: int = 10,
    ) -> None:
        """Initialize checkpoint manager."""
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_checkpoints = max_checkpoints
        self.max_opponents = max_opponents
        
        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.periodic_dir = self.checkpoint_dir / "checkpoints"
        self.periodic_dir.mkdir(exist_ok=True)
        self.opponents_dir = self.checkpoint_dir / "opponents"
        self.opponents_dir.mkdir(exist_ok=True)
        
        # Track best performance
        self.best_reward = float("-inf")
        self.best_win_rate = 0.0
    
    def save_checkpoint(
        self,
        agent: "Agent",
        episode: int,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save periodic checkpoint.
        
        Args:
            agent: Agent to save.
            episode: Current episode number.
            metadata: Additional metadata to save.
        
        Returns:
            Path to saved checkpoint.
        """
        filepath = self.periodic_dir / f"episode_{episode}.pt"
        
        # Save checkpoint
        agent.save(str(filepath))
        
        # Clean up old checkpoints
        self._cleanup_checkpoints()
        
        return filepath
    
    def save_latest(self, agent: "Agent", episode: int) -> Path:
        """Save as latest checkpoint (for resuming).
        
        Args:
            agent: Agent to save.
            episode: Current episode number.
        
        Returns:
            Path to latest checkpoint.
        """
        filepath = self.checkpoint_dir / "latest_model.pt"
        agent.save(str(filepath))
        return filepath
    
    def save_best(
        self,
        agent: "Agent",
        episode: int,
        reward: float,
        win_rate: float,
    ) -> Path | None:
        """Save as best checkpoint if performance improved.
        
        Args:
            agent: Agent to save.
            episode: Current episode number.
            reward: Current reward metric.
            win_rate: Current win rate.
        
        Returns:
            Path to best checkpoint if saved, None otherwise.
        """
        # Check if this is best performance
        improved = False
        
        if reward > self.best_reward:
            self.best_reward = reward
            improved = True
        
        if win_rate > self.best_win_rate:
            self.best_win_rate = win_rate
            improved = True
        
        if not improved:
            return None
        
        # Save as best
        filepath = self.checkpoint_dir / "best_model.pt"
        agent.save(str(filepath))
        
        print(f"New best model saved! (Episode {episode}, Reward: {reward:+.2f}, Win Rate: {win_rate:.1%})")
        
        return filepath
    
    def load_latest(self, agent_class: type["Agent"]) -> tuple["Agent", int] | None:
        """Load latest checkpoint for resuming.
        
        Args:
            agent_class: Agent class to instantiate.
        
        Returns:
            Tuple of (agent, episode) if checkpoint exists, None otherwise.
        """
        filepath = self.checkpoint_dir / "latest_model.pt"
        
        if not filepath.exists():
            return None
        
        try:
            agent = agent_class.load(str(filepath))
            episode = getattr(agent, "episodes_done", 0)
            print(f"Resumed from checkpoint: {filepath} (episode {episode})")
            return agent, episode
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            return None
    
    def load_best(self, agent_class: type["Agent"]) -> "Agent | None":
        """Load best checkpoint.
        
        Args:
            agent_class: Agent class to instantiate.
        
        Returns:
            Best agent if checkpoint exists, None otherwise.
        """
        filepath = self.checkpoint_dir / "best_model.pt"
        
        if not filepath.exists():
            return None
        
        try:
            agent = agent_class.load(str(filepath))
            print(f"Loaded best model from: {filepath}")
            return agent
        except Exception as e:
            print(f"Failed to load best checkpoint: {e}")
            return None
    
    def add_opponent(
        self,
        agent: "Agent",
        version: int,
        win_rate: float,
    ) -> Path:
        """Add agent to opponent pool for self-play.
        
        Args:
            agent: Agent to add to pool.
            version: Version number.
            win_rate: Win rate at time of addition.
        
        Returns:
            Path to opponent checkpoint.
        """
        filepath = self.opponents_dir / f"opponent_v{version}.pt"
        agent.save(str(filepath))
        
        print(f"Added opponent v{version} to pool (win_rate: {win_rate:.1%})")
        
        # Clean up old opponents
        self._cleanup_opponents()
        
        return filepath
    
    def load_random_opponent(self, agent_class: type["Agent"]) -> "Agent | None":
        """Load random opponent from pool.
        
        Args:
            agent_class: Agent class to instantiate.
        
        Returns:
            Random opponent agent if pool not empty, None otherwise.
        """
        import random
        
        opponents = list(self.opponents_dir.glob("opponent_*.pt"))
        
        if not opponents:
            return None
        
        filepath = random.choice(opponents)
        
        try:
            agent = agent_class.load(str(filepath))
            return agent
        except Exception as e:
            print(f"Failed to load opponent {filepath}: {e}")
            return None
    
    def get_opponent_count(self) -> int:
        """Get number of opponents in pool."""
        return len(list(self.opponents_dir.glob("opponent_*.pt")))
    
    def _cleanup_checkpoints(self) -> None:
        """Remove old periodic checkpoints, keeping only recent ones."""
        checkpoints = sorted(
            self.periodic_dir.glob("episode_*.pt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        # Remove oldest checkpoints beyond max
        for checkpoint in checkpoints[self.max_checkpoints :]:
            checkpoint.unlink()
    
    def _cleanup_opponents(self) -> None:
        """Remove old opponents, keeping only recent ones."""
        opponents = sorted(
            self.opponents_dir.glob("opponent_*.pt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        # Remove oldest opponents beyond max
        for opponent in opponents[self.max_opponents :]:
            opponent.unlink()
    
    def get_status(self) -> dict[str, Any]:
        """Get checkpoint manager status.
        
        Returns:
            Dictionary with checkpoint counts and paths.
        """
        return {
            "checkpoint_dir": str(self.checkpoint_dir),
            "has_latest": (self.checkpoint_dir / "latest_model.pt").exists(),
            "has_best": (self.checkpoint_dir / "best_model.pt").exists(),
            "periodic_checkpoints": len(list(self.periodic_dir.glob("episode_*.pt"))),
            "opponents_in_pool": self.get_opponent_count(),
            "best_reward": self.best_reward if self.best_reward > float("-inf") else None,
            "best_win_rate": self.best_win_rate,
        }
