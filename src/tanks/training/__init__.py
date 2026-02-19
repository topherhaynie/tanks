"""Training infrastructure for reinforcement learning.

This module provides headless training environments, episode management,
and reward functions for training RL agents.
"""

from tanks.training.env import TrainingEnvironment
from tanks.training.rewards import RewardCalculator

__all__ = [
    "RewardCalculator",
    "TrainingEnvironment",
]
