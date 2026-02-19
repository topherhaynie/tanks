"""Actor-Critic network architecture for PPO.

This module implements the neural network for Proximal Policy Optimization,
with shared feature extraction and separate actor (policy) and critic (value) heads.
"""

from typing import TYPE_CHECKING

import torch
import torch.nn as nn
from torch.distributions import Normal

if TYPE_CHECKING:
    pass


class ActorCriticNetwork(nn.Module):
    """Actor-Critic network with shared features for PPO.
    
    Architecture:
        Input (state_dim) → Shared Features (256→256)
                          ├→ Actor Head (128→action_dim) + Tanh
                          └→ Critic Head (128→1)
    
    The actor outputs action means for a Gaussian policy.
    The critic outputs a state value estimate.
    
    Args:
        state_dim: Dimension of input state vector.
        action_dim: Number of continuous action dimensions.
        hidden_dims: List of shared hidden layer sizes. Default: [256, 256].
        head_dim: Size of actor/critic head layers. Default: 128.
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: list[int] | None = None,
        head_dim: int = 128,
    ) -> None:
        """Initialize Actor-Critic network."""
        super().__init__()
        
        if hidden_dims is None:
            hidden_dims = [256, 256]
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Shared feature extractor
        shared_layers = []
        prev_dim = state_dim
        
        for hidden_dim in hidden_dims:
            shared_layers.append(nn.Linear(prev_dim, hidden_dim))
            shared_layers.append(nn.ReLU())
            prev_dim = hidden_dim
        
        self.shared = nn.Sequential(*shared_layers)
        
        # Actor head (policy)
        self.actor = nn.Sequential(
            nn.Linear(prev_dim, head_dim),
            nn.ReLU(),
            nn.Linear(head_dim, action_dim),
            nn.Tanh(),  # Output in [-1, 1]
        )
        
        # Critic head (value)
        self.critic = nn.Sequential(
            nn.Linear(prev_dim, head_dim),
            nn.ReLU(),
            nn.Linear(head_dim, 1),
        )
        
        # Action log std (learnable parameter, shared across actions)
        self.log_std = nn.Parameter(torch.zeros(action_dim))
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self) -> None:
        """Initialize network weights using orthogonal initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=1.0)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0.0)
    
    def forward(
        self,
        state: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass through network.
        
        Args:
            state: State tensor of shape (batch_size, state_dim) or (state_dim,).
        
        Returns:
            Tuple of (action_mean, action_std, value):
            - action_mean: Mean actions (batch_size, action_dim)
            - action_std: Action standard deviation (batch_size, action_dim)
            - value: State value estimate (batch_size, 1) or scalar
        """
        # Shared features
        features = self.shared(state)
        
        # Actor: action distribution parameters
        action_mean = self.actor(features)
        action_std = torch.exp(self.log_std).expand_as(action_mean)
        
        # Critic: state value
        value = self.critic(features)
        
        return action_mean, action_std, value
    
    def get_action(
        self,
        state: torch.Tensor,
        deterministic: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Sample action from policy.
        
        Args:
            state: State tensor (batch_size, state_dim) or (state_dim,).
            deterministic: If True, return mean action. If False, sample.
        
        Returns:
            Tuple of (action, log_prob, value):
            - action: Sampled action (batch_size, action_dim) or (action_dim,)
            - log_prob: Log probability of action (batch_size,) or scalar
            - value: State value estimate (batch_size,) or scalar
        """
        action_mean, action_std, value = self.forward(state)
        
        if deterministic:
            action = action_mean
        else:
            # Sample from Gaussian distribution
            dist = Normal(action_mean, action_std)
            action = dist.sample()
        
        # Compute log probability
        dist = Normal(action_mean, action_std)
        log_prob = dist.log_prob(action).sum(dim=-1)
        
        return action, log_prob, value.squeeze(-1)
    
    def evaluate_actions(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate actions for PPO update.
        
        Args:
            state: State tensor (batch_size, state_dim).
            action: Action tensor (batch_size, action_dim).
        
        Returns:
            Tuple of (log_prob, entropy, value):
            - log_prob: Log probability of actions (batch_size,)
            - entropy: Entropy of policy (batch_size,)
            - value: State value estimate (batch_size,)
        """
        action_mean, action_std, value = self.forward(state)
        
        # Create distribution
        dist = Normal(action_mean, action_std)
        
        # Compute log probability and entropy
        log_prob = dist.log_prob(action).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        
        return log_prob, entropy, value.squeeze(-1)
    
    def get_value(self, state: torch.Tensor) -> torch.Tensor:
        """Get state value estimate.
        
        Args:
            state: State tensor (batch_size, state_dim) or (state_dim,).
        
        Returns:
            Value estimate (batch_size,) or scalar.
        """
        features = self.shared(state)
        value = self.critic(features)
        return value.squeeze(-1)


class SeparateActorCriticNetwork(nn.Module):
    """Actor-Critic with completely separate networks.
    
    This architecture has no shared layers between actor and critic,
    which can be more stable but less sample-efficient.
    
    Args:
        state_dim: Dimension of input state vector.
        action_dim: Number of continuous action dimensions.
        actor_dims: List of actor hidden layer sizes. Default: [256, 256, 128].
        critic_dims: List of critic hidden layer sizes. Default: [256, 256, 128].
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        actor_dims: list[int] | None = None,
        critic_dims: list[int] | None = None,
    ) -> None:
        """Initialize separate Actor-Critic network."""
        super().__init__()
        
        if actor_dims is None:
            actor_dims = [256, 256, 128]
        if critic_dims is None:
            critic_dims = [256, 256, 128]
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Actor network
        actor_layers = []
        prev_dim = state_dim
        for hidden_dim in actor_dims:
            actor_layers.append(nn.Linear(prev_dim, hidden_dim))
            actor_layers.append(nn.ReLU())
            prev_dim = hidden_dim
        actor_layers.append(nn.Linear(prev_dim, action_dim))
        actor_layers.append(nn.Tanh())
        
        self.actor = nn.Sequential(*actor_layers)
        
        # Critic network
        critic_layers = []
        prev_dim = state_dim
        for hidden_dim in critic_dims:
            critic_layers.append(nn.Linear(prev_dim, hidden_dim))
            critic_layers.append(nn.ReLU())
            prev_dim = hidden_dim
        critic_layers.append(nn.Linear(prev_dim, 1))
        
        self.critic = nn.Sequential(*critic_layers)
        
        # Action log std
        self.log_std = nn.Parameter(torch.zeros(action_dim))
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self) -> None:
        """Initialize network weights using orthogonal initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=1.0)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0.0)
    
    def forward(
        self,
        state: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass through both networks.
        
        Args:
            state: State tensor of shape (batch_size, state_dim) or (state_dim,).
        
        Returns:
            Tuple of (action_mean, action_std, value).
        """
        action_mean = self.actor(state)
        action_std = torch.exp(self.log_std).expand_as(action_mean)
        value = self.critic(state)
        
        return action_mean, action_std, value
    
    def get_action(
        self,
        state: torch.Tensor,
        deterministic: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Sample action from policy."""
        action_mean, action_std, value = self.forward(state)
        
        if deterministic:
            action = action_mean
        else:
            dist = Normal(action_mean, action_std)
            action = dist.sample()
        
        dist = Normal(action_mean, action_std)
        log_prob = dist.log_prob(action).sum(dim=-1)
        
        return action, log_prob, value.squeeze(-1)
    
    def evaluate_actions(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate actions for PPO update."""
        action_mean, action_std, value = self.forward(state)
        
        dist = Normal(action_mean, action_std)
        log_prob = dist.log_prob(action).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        
        return log_prob, entropy, value.squeeze(-1)
    
    def get_value(self, state: torch.Tensor) -> torch.Tensor:
        """Get state value estimate."""
        value = self.critic(state)
        return value.squeeze(-1)
