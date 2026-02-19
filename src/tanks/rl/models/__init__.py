"""Neural network models for reinforcement learning.

This module contains DQN, PPO, and other RL network architectures,
as well as the base Agent interface for RL agents.
"""

from tanks.rl.models.agent import Agent, DQNAgent, PPOAgent, RandomAgent
from tanks.rl.models.dqn import DQNNetwork, DuelingDQNNetwork
from tanks.rl.models.ppo import ActorCriticNetwork, SeparateActorCriticNetwork

__all__ = [
    "ActorCriticNetwork",
    "Agent",
    "DQNAgent",
    "DQNNetwork",
    "DuelingDQNNetwork",
    "PPOAgent",
    "RandomAgent",
    "SeparateActorCriticNetwork",
]
