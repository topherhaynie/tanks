"""Base agent interface for RL agents.

This module defines the abstract interface that all RL agents (DQN, PPO, etc.)
must implement to be compatible with RLBot wrapper.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
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


class PPOAgent(Agent):
    """Proximal Policy Optimization agent for continuous action spaces.

    Uses an actor-critic network to learn both policy and value function.
    Implements PPO-Clip algorithm for stable policy updates.

    Args:
        state_dim: Dimension of state vector.
        action_dim: Number of continuous action dimensions.
        learning_rate: Learning rate for optimizer. Default: 3e-4.
        gamma: Discount factor for future rewards. Default: 0.99.
        gae_lambda: Lambda for Generalized Advantage Estimation. Default: 0.95.
        clip_epsilon: PPO clipping parameter. Default: 0.2.
        value_loss_coef: Coefficient for value loss. Default: 0.5.
        entropy_coef: Coefficient for entropy bonus. Default: 0.01.
        max_grad_norm: Maximum gradient norm for clipping. Default: 0.5.
        device: Torch device (cpu or cuda). Default: auto-detect.
        network_type: Architecture ('shared' or 'separate'). Default: 'shared'.

    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_loss_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        device: str | None = None,
        network_type: str = "shared",
    ) -> None:
        """Initialize PPO agent."""
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm

        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Create network
        from tanks.rl.models.ppo import ActorCriticNetwork, SeparateActorCriticNetwork

        if network_type == "separate":
            self.network = SeparateActorCriticNetwork(state_dim, action_dim).to(self.device)
        else:
            self.network = ActorCriticNetwork(state_dim, action_dim).to(self.device)

        # Optimizer
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)

        # Training stats
        self.steps_done = 0
        self.episodes_done = 0

    def predict(self, state: np.ndarray, deterministic: bool = True) -> int:
        """Predict action from state (returns int for compatibility).

        For PPO, this converts continuous actions to a discrete index.
        Use get_action() for actual continuous actions.

        Args:
            state: State vector from state encoder.
            deterministic: If True, use mean action. If False, sample.

        Returns:
            Placeholder action index (always 0 for continuous).

        """
        # For compatibility with Bot interface, but PPO uses continuous actions
        return 0

    def get_action(
        self,
        state: np.ndarray,
        deterministic: bool = False,
    ) -> tuple[np.ndarray, float, float]:
        """Get continuous action from policy.

        Args:
            state: State vector.
            deterministic: If True, return mean. If False, sample.

        Returns:
            Tuple of (action, log_prob, value):
            - action: Continuous action array (action_dim,)
            - log_prob: Log probability of action
            - value: State value estimate

        """
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            action, log_prob, value = self.network.get_action(state_tensor, deterministic)

            return (
                action.cpu().numpy()[0],
                float(log_prob.item()),
                float(value.item()),
            )

    def compute_gae(
        self,
        rewards: np.ndarray,
        values: np.ndarray,
        dones: np.ndarray,
        next_value: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute Generalized Advantage Estimation.

        Args:
            rewards: Array of rewards (timesteps,).
            values: Array of value estimates (timesteps,).
            dones: Array of done flags (timesteps,).
            next_value: Value estimate for state after last timestep.

        Returns:
            Tuple of (advantages, returns):
            - advantages: GAE advantages (timesteps,)
            - returns: Value targets (timesteps,)

        """
        advantages = np.zeros_like(rewards, dtype=np.float32)
        last_gae = 0.0

        # Compute GAE backwards from final timestep
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_val = next_value
            else:
                next_val = values[t + 1]

            # TD error: δ_t = r_t + γV(s_{t+1}) - V(s_t)
            delta = rewards[t] + self.gamma * next_val * (1 - dones[t]) - values[t]

            # GAE: A_t = δ_t + (γλ)δ_{t+1} + (γλ)²δ_{t+2} + ...
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * last_gae

        # Returns are advantages + values
        returns = advantages + values

        return advantages, returns

    def train_step(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        old_log_probs: np.ndarray,
        advantages: np.ndarray,
        returns: np.ndarray,
    ) -> dict[str, float]:
        """Perform one PPO training step.

        Args:
            states: Batch of states (batch_size, state_dim).
            actions: Batch of actions (batch_size, action_dim).
            old_log_probs: Old log probabilities (batch_size,).
            advantages: Computed advantages (batch_size,).
            returns: Value targets (batch_size,).

        Returns:
            Dictionary of loss components.

        """
        # Convert to tensors
        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.FloatTensor(actions).to(self.device)
        old_log_probs_t = torch.FloatTensor(old_log_probs).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)

        # Normalize advantages
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)

        # Evaluate actions with current policy
        log_probs, entropy, values = self.network.evaluate_actions(states_t, actions_t)

        # Compute ratio: π_new / π_old
        ratio = torch.exp(log_probs - old_log_probs_t)

        # Compute clipped surrogate objective
        surr1 = ratio * advantages_t
        surr2 = torch.clamp(ratio, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon) * advantages_t
        policy_loss = -torch.min(surr1, surr2).mean()

        # Compute clip fraction (percentage of samples clipped)
        clip_fraction = float((torch.abs(ratio - 1.0) > self.clip_epsilon).float().mean().item())

        # Compute value loss
        value_loss = F.mse_loss(values, returns_t)

        # Compute entropy bonus
        entropy_loss = -entropy.mean()

        # Total loss
        total_loss = policy_loss + self.value_loss_coef * value_loss + self.entropy_coef * entropy_loss

        # Optimize
        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
        self.optimizer.step()

        self.steps_done += 1

        return {
            "total_loss": float(total_loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy_loss": float(entropy_loss.item()),
            "entropy": float(entropy.mean().item()),  # Also return raw entropy
            "clip_fraction": clip_fraction,
            "ratio_mean": float(ratio.mean().item()),
        }

    def save(self, path: str) -> None:
        """Save agent checkpoint.

        Args:
            path: File path to save checkpoint.

        """
        checkpoint = self.create_checkpoint()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, path)

    def create_checkpoint(self) -> dict:
        """Create checkpoint dictionary.

        Returns:
            Checkpoint dictionary with all agent state.

        """
        # Deep copy state dicts to avoid reference issues
        network_state = {k: v.clone() for k, v in self.network.state_dict().items()}
        optimizer_state = {
            k: {kk: vv.clone() if isinstance(vv, torch.Tensor) else vv for kk, vv in v.items()}
            if isinstance(v, dict)
            else v
            for k, v in self.optimizer.state_dict().items()
        }

        return {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "network_state_dict": network_state,
            "optimizer_state_dict": optimizer_state,
            "steps_done": self.steps_done,
            "episodes_done": self.episodes_done,
            "gamma": self.gamma,
            "gae_lambda": self.gae_lambda,
            "clip_epsilon": self.clip_epsilon,
            "value_loss_coef": self.value_loss_coef,
            "entropy_coef": self.entropy_coef,
            "max_grad_norm": self.max_grad_norm,
        }

    def load_checkpoint(self, checkpoint: dict) -> None:
        """Load agent from checkpoint dictionary.

        Args:
            checkpoint: Checkpoint dictionary.

        """
        self.network.load_state_dict(checkpoint["network_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.steps_done = checkpoint.get("steps_done", 0)
        self.episodes_done = checkpoint.get("episodes_done", 0)

    @classmethod
    def load(cls, path: str, device: str | None = None) -> "PPOAgent":
        """Load agent from checkpoint.

        Args:
            path: File path to load checkpoint from.
            device: Device to load model on. Default: auto-detect.

        Returns:
            Loaded PPO agent.

        """
        checkpoint = torch.load(path, map_location=device or "cpu", weights_only=True)

        agent = cls(
            state_dim=checkpoint["state_dim"],
            action_dim=checkpoint["action_dim"],
            gamma=checkpoint.get("gamma", 0.99),
            gae_lambda=checkpoint.get("gae_lambda", 0.95),
            clip_epsilon=checkpoint.get("clip_epsilon", 0.2),
            value_loss_coef=checkpoint.get("value_loss_coef", 0.5),
            entropy_coef=checkpoint.get("entropy_coef", 0.01),
            max_grad_norm=checkpoint.get("max_grad_norm", 0.5),
            device=device,
        )

        agent.network.load_state_dict(checkpoint["network_state_dict"])
        agent.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        agent.steps_done = checkpoint.get("steps_done", 0)
        agent.episodes_done = checkpoint.get("episodes_done", 0)

        return agent
