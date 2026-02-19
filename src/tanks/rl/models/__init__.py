"""Neural network models for reinforcement learning.

This module contains DQN, PPO, and other RL network architectures,
as well as the base Agent interface for RL agents.
"""

from tanks.rl.models.agent import Agent, DQNAgent, RandomAgent
from tanks.rl.models.dqn import DQNNetwork, DuelingDQNNetwork

__all__ = [
    "Agent",
    "DQNAgent",
    "DQNNetwork",
    "DuelingDQNNetwork",
    "RandomAgent",
]
