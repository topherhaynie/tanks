"""Base agent interface for RL agents.

This module defines the abstract interface that all RL agents (DQN, PPO, etc.)
must implement to be compatible with RLBot wrapper.
"""

from abc import ABC, abstractmethod

import numpy as np


class Agent(ABC):
    """Abstract base class for RL agents.

    All concrete agent implementations (DQNAgent, PPOAgent, etc.) should
    inherit from this class and implement the predict method.
    """

    @abstractmethod
    def predict(self, state: np.ndarray, deterministic: bool = True) -> int:
        """Predict action from state.

        Args:
            state: State vector from StateEncoder (78-dim for current encoding).
            deterministic: If True, return best action. If False, sample from policy.

        Returns:
            Action index (int for discrete actions).

        """

    @abstractmethod
    def save(self, path: str) -> None:
        """Save agent to file.

        Args:
            path: File path to save checkpoint.

        """

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> "Agent":
        """Load agent from file.

        Args:
            path: File path to load checkpoint from.

        Returns:
            Loaded agent instance.

        """


class RandomAgent(Agent):
    """Random agent for testing and baseline comparison."""

    def __init__(self, num_actions: int = 12) -> None:
        """Initialize random agent.

        Args:
            num_actions: Number of discrete actions in action space.

        """
        self.num_actions = num_actions

    def predict(self, state: np.ndarray, deterministic: bool = True) -> int:
        """Return random action.

        Args:
            state: State vector (ignored).
            deterministic: Flag (ignored for random agent).

        Returns:
            Random action index.

        """
        return int(np.random.randint(0, self.num_actions))

    def save(self, path: str) -> None:
        """Save random agent (no-op).

        Args:
            path: File path (ignored).

        """

    @classmethod
    def load(cls, path: str) -> "RandomAgent":
        """Load random agent.

        Args:
            path: File path (ignored).

        Returns:
            New random agent.

        """
        return cls()
