"""Base agent interface for RL agents.

This module defines the abstract interface that all RL agents (DQN, PPO, etc.)
must implement to be compatible with RLBot wrapper.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import torch
from torch import nn, optim


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


class DQNAgent(Agent):
    """Deep Q-Network agent for discrete action spaces.

    Uses a neural network to approximate Q-values for state-action pairs.
    Implements epsilon-greedy exploration and target network for stability.

    Args:
        state_dim: Dimension of state vector.
        action_dim: Number of discrete actions.
        learning_rate: Learning rate for optimizer. Default: 1e-4.
        gamma: Discount factor for future rewards. Default: 0.99.
        epsilon: Initial exploration rate. Default: 1.0.
        epsilon_min: Minimum exploration rate. Default: 0.05.
        epsilon_decay: Decay rate per episode. Default: 0.995.
        device: Torch device (cpu or cuda). Default: auto-detect.
        network_type: Network architecture ('dqn' or 'dueling'). Default: 'dqn'.

    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 1e-4,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        device: str | None = None,
        network_type: str = "dqn",
    ) -> None:
        """Initialize DQN agent."""
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Create networks
        from tanks.rl.models.dqn import DQNNetwork, DuelingDQNNetwork

        if network_type == "dueling":
            self.policy_net = DuelingDQNNetwork(state_dim, action_dim).to(self.device)
            self.target_net = DuelingDQNNetwork(state_dim, action_dim).to(self.device)
        else:
            self.policy_net = DQNNetwork(state_dim, action_dim).to(self.device)
            self.target_net = DQNNetwork(state_dim, action_dim).to(self.device)

        # Initialize target network with policy network weights
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()  # Target network is never trained directly

        # Optimizer and loss
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.criterion = nn.SmoothL1Loss()  # Huber loss (more stable than MSE)

        # Training stats
        self.steps_done = 0
        self.episodes_done = 0

    def predict(self, state: np.ndarray, deterministic: bool = True) -> int:
        """Predict action from state.

        Args:
            state: State vector from state encoder.
            deterministic: If True, use greedy policy. If False, use epsilon-greedy.

        Returns:
            Action index.

        """
        # Epsilon-greedy exploration (only if not deterministic)
        if not deterministic and np.random.random() < self.epsilon:
            return int(np.random.randint(0, self.action_dim))

        # Greedy action selection
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return int(q_values.argmax(dim=1).item())

    def select_action(self, state: np.ndarray) -> int:
        """Select action with epsilon-greedy exploration.

        This is the training-time action selection method. Use predict()
        for deployment (which has deterministic flag).

        Args:
            state: State vector.

        Returns:
            Action index.

        """
        return self.predict(state, deterministic=False)

    def train_step(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
    ) -> float:
        """Perform one training step on a batch of experiences.

        Args:
            states: Batch of states (batch_size, state_dim).
            actions: Batch of actions (batch_size,).
            rewards: Batch of rewards (batch_size,).
            next_states: Batch of next states (batch_size, state_dim).
            dones: Batch of done flags (batch_size,).

        Returns:
            Training loss value.

        """
        # Convert to tensors
        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards_t = torch.FloatTensor(rewards).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t = torch.FloatTensor(dones.astype(float)).to(self.device)

        # Compute Q(s, a) - Q-values for taken actions
        q_values = self.policy_net(states_t).gather(1, actions_t).squeeze()

        # Compute target Q-values: r + gamma * max_a' Q_target(s', a')
        with torch.no_grad():
            next_q_values = self.target_net(next_states_t).max(dim=1)[0]
            target_q_values = rewards_t + self.gamma * next_q_values * (1 - dones_t)

        # Compute loss and backpropagate
        loss = self.criterion(q_values, target_q_values)

        self.optimizer.zero_grad()
        loss.backward()

        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=1.0)

        self.optimizer.step()

        self.steps_done += 1

        return float(loss.item())

    def update_target_network(self) -> None:
        """Update target network with policy network weights."""
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def decay_epsilon(self) -> None:
        """Decay epsilon after episode."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.episodes_done += 1

    def save(self, path: str) -> None:
        """Save agent checkpoint.

        Args:
            path: File path to save checkpoint.

        """
        checkpoint = {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "policy_net_state_dict": self.policy_net.state_dict(),
            "target_net_state_dict": self.target_net.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
            "steps_done": self.steps_done,
            "episodes_done": self.episodes_done,
            "gamma": self.gamma,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, path)

    @classmethod
    def load(cls, path: str, device: str | None = None) -> "DQNAgent":
        """Load agent from checkpoint.

        Args:
            path: File path to load checkpoint from.
            device: Device to load model on. Default: auto-detect.

        Returns:
            Loaded DQN agent.

        """
        checkpoint = torch.load(path, map_location=device or "cpu", weights_only=True)

        agent = cls(
            state_dim=checkpoint["state_dim"],
            action_dim=checkpoint["action_dim"],
            gamma=checkpoint.get("gamma", 0.99),
            epsilon=checkpoint["epsilon"],
            epsilon_min=checkpoint.get("epsilon_min", 0.05),
            epsilon_decay=checkpoint.get("epsilon_decay", 0.995),
            device=device,
        )

        agent.policy_net.load_state_dict(checkpoint["policy_net_state_dict"])
        agent.target_net.load_state_dict(checkpoint["target_net_state_dict"])
        agent.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        agent.steps_done = checkpoint.get("steps_done", 0)
        agent.episodes_done = checkpoint.get("episodes_done", 0)

        return agent
