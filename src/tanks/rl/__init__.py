"""Reinforcement learning infrastructure.

This module provides state representation, action spaces, neural networks,
training algorithms, and metrics for RL-based bot development.
"""

from tanks.rl.actions import ActionSpace, DiscreteActionSpace
from tanks.rl.state import StateEncoder

__all__ = [
    "ActionSpace",
    "DiscreteActionSpace",
    "StateEncoder",
]
