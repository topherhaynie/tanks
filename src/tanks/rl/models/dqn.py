"""Deep Q-Network architecture for reinforcement learning.

This module implements the neural network architecture for DQN-based agents.
The network takes vectorized game state as input and outputs Q-values for each action.
"""

import torch
from torch import nn


class DQNNetwork(nn.Module):
    """Deep Q-Network with 3-layer fully connected architecture.

    Architecture:
        Input (state_dim) → Dense(256) → ReLU → Dropout(0.2)
                          → Dense(256) → ReLU → Dropout(0.2)
                          → Dense(128) → ReLU
                          → Output (action_dim)

    Args:
        state_dim: Dimension of input state vector.
        action_dim: Number of discrete actions.
        hidden_dims: List of hidden layer sizes. Default: [256, 256, 128].
        dropout: Dropout probability. Default: 0.2.

    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: list[int] | None = None,
        dropout: float = 0.2,
    ) -> None:
        """Initialize DQN network."""
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [256, 256, 128]

        self.state_dim = state_dim
        self.action_dim = action_dim

        # Build network layers
        layers = []
        prev_dim = state_dim

        for i, hidden_dim in enumerate(hidden_dims):
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())

            # Add dropout to first two layers
            if i < 2 and dropout > 0:
                layers.append(nn.Dropout(dropout))

            prev_dim = hidden_dim

        # Output layer
        layers.append(nn.Linear(prev_dim, action_dim))

        self.network = nn.Sequential(*layers)

        # Initialize weights
        self._initialize_weights()

    def _initialize_weights(self) -> None:
        """Initialize network weights using Xavier initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0.0)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass through network.

        Args:
            state: State tensor of shape (batch_size, state_dim) or (state_dim,).

        Returns:
            Q-values tensor of shape (batch_size, action_dim) or (action_dim,).

        """
        return self.network(state)


class DuelingDQNNetwork(nn.Module):
    """Dueling DQN architecture with separate value and advantage streams.

    Splits the network into:
        - Value stream: V(s) - scalar value of state
        - Advantage stream: A(s,a) - advantage of each action
        - Final Q-values: Q(s,a) = V(s) + (A(s,a) - mean(A(s)))

    This architecture learns which states are valuable independently of action effects.

    Args:
        state_dim: Dimension of input state vector.
        action_dim: Number of discrete actions.
        hidden_dims: List of shared hidden layer sizes. Default: [256, 256].
        stream_dim: Dimension of value/advantage streams. Default: 128.
        dropout: Dropout probability. Default: 0.2.

    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: list[int] | None = None,
        stream_dim: int = 128,
        dropout: float = 0.2,
    ) -> None:
        """Initialize Dueling DQN network."""
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [256, 256]

        self.state_dim = state_dim
        self.action_dim = action_dim

        # Shared feature extraction layers
        shared_layers = []
        prev_dim = state_dim

        for i, hidden_dim in enumerate(hidden_dims):
            shared_layers.append(nn.Linear(prev_dim, hidden_dim))
            shared_layers.append(nn.ReLU())

            if dropout > 0:
                shared_layers.append(nn.Dropout(dropout))

            prev_dim = hidden_dim

        self.shared = nn.Sequential(*shared_layers)

        # Value stream: V(s)
        self.value_stream = nn.Sequential(
            nn.Linear(prev_dim, stream_dim),
            nn.ReLU(),
            nn.Linear(stream_dim, 1),
        )

        # Advantage stream: A(s,a)
        self.advantage_stream = nn.Sequential(
            nn.Linear(prev_dim, stream_dim),
            nn.ReLU(),
            nn.Linear(stream_dim, action_dim),
        )

        # Initialize weights
        self._initialize_weights()

    def _initialize_weights(self) -> None:
        """Initialize network weights using Xavier initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0.0)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass through dueling architecture.

        Args:
            state: State tensor of shape (batch_size, state_dim) or (state_dim,).

        Returns:
            Q-values tensor of shape (batch_size, action_dim) or (action_dim,).

        """
        # Shared feature extraction
        features = self.shared(state)

        # Value and advantage streams
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)

        # Combine: Q(s,a) = V(s) + (A(s,a) - mean(A(s)))
        # Subtracting mean advantage makes the representation unique
        q_values = value + (advantage - advantage.mean(dim=-1, keepdim=True))

        return q_values
