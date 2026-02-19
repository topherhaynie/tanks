"""Episode management for training.

Provides utilities for episode lifecycle, data collection, and metrics tracking.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from tanks.training.env import TrainingEnvironment


@dataclass
class Episode:
    """Container for episode data."""

    episode_id: int
    observations: list[np.ndarray] = field(default_factory=list)
    actions: list[int | np.ndarray] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    dones: list[bool] = field(default_factory=list)
    infos: list[dict] = field(default_factory=list)

    def add_step(
        self,
        observation: np.ndarray,
        action: int | np.ndarray,
        reward: float,
        done: bool,
        info: dict,
    ) -> None:
        """Add a step to the episode.

        Args:
            observation: Observation at this step.
            action: Action taken at this step.
            reward: Reward received at this step.
            done: Whether episode ended at this step.
            info: Additional info for this step.

        """
        self.observations.append(observation)
        self.actions.append(action)
        self.rewards.append(reward)
        self.dones.append(done)
        self.infos.append(info)

    def get_total_reward(self) -> float:
        """Get total episode reward.

        Returns:
            Sum of all rewards.

        """
        return sum(self.rewards)

    def get_length(self) -> int:
        """Get episode length in steps.

        Returns:
            Number of steps in episode.

        """
        return len(self.rewards)

    def get_final_info(self) -> dict:
        """Get final step info.

        Returns:
            Info dict from last step, or empty dict if no steps.

        """
        return self.infos[-1] if self.infos else {}


class EpisodeManager:
    """Manages episode collection and metrics for training."""

    def __init__(self) -> None:
        """Initialize episode manager."""
        self.episodes: list[Episode] = []
        self.current_episode: Episode | None = None
        self.episode_counter = 0

    def start_episode(self) -> None:
        """Start a new episode."""
        self.current_episode = Episode(episode_id=self.episode_counter)
        self.episode_counter += 1

    def add_step(
        self,
        observation: np.ndarray,
        action: int | np.ndarray,
        reward: float,
        done: bool,
        info: dict,
    ) -> None:
        """Add a step to current episode.

        Args:
            observation: Observation at this step.
            action: Action taken at this step.
            reward: Reward received at this step.
            done: Whether episode ended at this step.
            info: Additional info for this step.

        """
        if self.current_episode is None:
            self.start_episode()

        self.current_episode.add_step(observation, action, reward, done, info)

    def end_episode(self) -> Episode:
        """End current episode and return it.

        Returns:
            Completed episode.

        Raises:
            RuntimeError: If no episode is in progress.

        """
        if self.current_episode is None:
            msg = "No episode in progress"
            raise RuntimeError(msg)

        episode = self.current_episode
        self.episodes.append(episode)
        self.current_episode = None
        return episode

    def get_recent_stats(self, n: int = 100) -> dict[str, float]:
        """Get statistics for recent episodes.

        Args:
            n: Number of recent episodes to consider.

        Returns:
            Dictionary with mean and std of rewards and lengths.

        """
        if not self.episodes:
            return {
                "mean_reward": 0.0,
                "std_reward": 0.0,
                "mean_length": 0.0,
                "std_length": 0.0,
            }

        recent = self.episodes[-n:]
        rewards = [ep.get_total_reward() for ep in recent]
        lengths = [ep.get_length() for ep in recent]

        return {
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "mean_length": float(np.mean(lengths)),
            "std_length": float(np.std(lengths)),
        }

    def clear(self) -> None:
        """Clear all episode history."""
        self.episodes.clear()
        self.current_episode = None


def run_episode(
    env: "TrainingEnvironment",
    agent_fn,  # type: ignore[no-untyped-def]
    max_steps: int | None = None,
) -> Episode:
    """Run a single episode with given agent.

    Args:
        env: Training environment.
        agent_fn: Function that takes observation and returns action.
        max_steps: Maximum steps per episode. Uses env default if None.

    Returns:
        Completed episode with all data.

    """
    episode = Episode(episode_id=0)
    observation = env.reset()

    done = False
    step = 0

    while not done:
        # Get action from agent
        action = agent_fn(observation)

        # Step environment
        next_observation, reward, done, info = env.step(action)

        # Record step
        episode.add_step(observation, action, reward, done, info)

        observation = next_observation
        step += 1

        # Check max steps
        if max_steps and step >= max_steps:
            break

    return episode


def collect_episodes(
    env: "TrainingEnvironment",
    agent_fn,  # type: ignore[no-untyped-def]
    n_episodes: int,
    max_steps: int | None = None,
) -> list[Episode]:
    """Collect multiple episodes.

    Args:
        env: Training environment.
        agent_fn: Function that takes observation and returns action.
        n_episodes: Number of episodes to collect.
        max_steps: Maximum steps per episode.

    Returns:
        List of completed episodes.

    """
    episodes = []

    for i in range(n_episodes):
        episode = run_episode(env, agent_fn, max_steps)
        episode.episode_id = i
        episodes.append(episode)

    return episodes
