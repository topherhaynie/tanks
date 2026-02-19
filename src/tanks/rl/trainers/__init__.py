"""Training algorithms and loops for RL agents.

This module contains DQN, PPO trainers, self-play, curriculum, and co-evolution logic.
"""

from tanks.rl.trainers.curriculum import CurriculumStage, CurriculumTrainer
from tanks.rl.trainers.dqn_trainer import DQNTrainer
from tanks.rl.trainers.ppo_trainer import PPOTrainer
from tanks.rl.trainers.self_play import SelfPlayTrainer

__all__ = [
    "CurriculumStage",
    "CurriculumTrainer",
    "DQNTrainer",
    "PPOTrainer",
    "SelfPlayTrainer",
]
