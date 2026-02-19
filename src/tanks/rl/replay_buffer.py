"""Experience replay buffer for DQN training.

This module implements a circular buffer for storing and sampling past experiences.
The buffer uses efficient numpy arrays for fast sampling and memory management.
"""

import numpy as np


class ReplayBuffer:
    """Circular buffer for storing (state, action, reward, next_state, done) experiences.

    The buffer stores experiences efficiently using numpy arrays and supports
    uniform random sampling for training. When the buffer is full, old experiences
    are overwritten in a circular fashion.

    Args:
        capacity: Maximum number of experiences to store.
        state_dim: Dimension of state vectors.

    Attributes:
        size: Current number of experiences stored.
        capacity: Maximum buffer capacity.

    """

    def __init__(self, capacity: int, state_dim: int) -> None:
        """Initialize replay buffer."""
        self.capacity = capacity
        self.state_dim = state_dim
        self.size = 0
        self.position = 0

        # Preallocate memory for efficiency
        self.states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.actions = np.zeros(capacity, dtype=np.int64)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=bool)

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """Add an experience to the buffer.

        Args:
            state: Current state vector.
            action: Action taken (discrete index).
            reward: Reward received.
            next_state: Resulting state vector.
            done: Whether the episode terminated.

        """
        self.states[self.position] = state
        self.actions[self.position] = action
        self.rewards[self.position] = reward
        self.next_states[self.position] = next_state
        self.dones[self.position] = done

        # Update position (circular)
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(
        self, batch_size: int
    ) -> tuple[
        np.ndarray,  # states
        np.ndarray,  # actions
        np.ndarray,  # rewards
        np.ndarray,  # next_states
        np.ndarray,  # dones
    ]:
        """Sample a random batch of experiences.

        Args:
            batch_size: Number of experiences to sample.

        Returns:
            Tuple of (states, actions, rewards, next_states, dones) as numpy arrays.

        Raises:
            ValueError: If batch_size > current buffer size.

        """
        if batch_size > self.size:
            error_msg = f"Cannot sample {batch_size} experiences from buffer with {self.size} items"
            raise ValueError(error_msg)

        # Sample random indices
        indices = np.random.choice(self.size, batch_size, replace=False)

        return (
            self.states[indices],
            self.actions[indices],
            self.rewards[indices],
            self.next_states[indices],
            self.dones[indices],
        )

    def __len__(self) -> int:
        """Return current buffer size."""
        return self.size

    def clear(self) -> None:
        """Clear all experiences from buffer."""
        self.size = 0
        self.position = 0


class PrioritizedReplayBuffer(ReplayBuffer):
    """Prioritized experience replay buffer (future enhancement).

    Samples experiences based on their TD error, giving priority to
    experiences the agent can learn more from. This typically accelerates
    training and improves final performance.

    Args:
        capacity: Maximum number of experiences to store.
        state_dim: Dimension of state vectors.
        alpha: Prioritization exponent (0 = uniform, 1 = full prioritization).
        beta_start: Initial importance sampling exponent.
        beta_end: Final importance sampling exponent.
        beta_frames: Number of frames to anneal beta from start to end.

    """

    def __init__(
        self,
        capacity: int,
        state_dim: int,
        alpha: float = 0.6,
        beta_start: float = 0.4,
        beta_end: float = 1.0,
        beta_frames: int = 100000,
    ) -> None:
        """Initialize prioritized replay buffer."""
        super().__init__(capacity, state_dim)

        self.alpha = alpha
        self.beta_start = beta_start
        self.beta_end = beta_end
        self.beta_frames = beta_frames
        self.frame = 0

        # Priority tree (sum tree for efficient sampling)
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.max_priority = 1.0

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """Add experience with maximum priority."""
        super().add(state, action, reward, next_state, done)

        # Assign maximum priority to new experience
        self.priorities[self.position - 1] = self.max_priority

    def sample(
        self, batch_size: int
    ) -> tuple[
        np.ndarray,  # states
        np.ndarray,  # actions
        np.ndarray,  # rewards
        np.ndarray,  # next_states
        np.ndarray,  # dones
        np.ndarray,  # indices
        np.ndarray,  # weights
    ]:
        """Sample batch with priority-based sampling.

        Args:
            batch_size: Number of experiences to sample.

        Returns:
            Tuple of (states, actions, rewards, next_states, dones, indices, weights).
            Weights are importance sampling weights to correct for bias.

        """
        if batch_size > self.size:
            error_msg = f"Cannot sample {batch_size} experiences from buffer with {self.size} items"
            raise ValueError(error_msg)

        # Calculate sampling probabilities
        priorities = self.priorities[: self.size] ** self.alpha
        probabilities = priorities / priorities.sum()

        # Sample indices based on priorities
        indices = np.random.choice(self.size, batch_size, replace=False, p=probabilities)

        # Calculate importance sampling weights
        self.frame += 1
        beta = self._get_beta()
        weights = (self.size * probabilities[indices]) ** (-beta)
        weights /= weights.max()  # Normalize for stability

        return (
            self.states[indices],
            self.actions[indices],
            self.rewards[indices],
            self.next_states[indices],
            self.dones[indices],
            indices,
            weights,
        )

    def update_priorities(self, indices: np.ndarray, priorities: np.ndarray) -> None:
        """Update priorities for sampled experiences.

        Args:
            indices: Indices of experiences to update.
            priorities: New priority values (typically TD errors).

        """
        for idx, priority in zip(indices, priorities, strict=False):
            self.priorities[idx] = priority
            self.max_priority = max(self.max_priority, priority)

    def _get_beta(self) -> float:
        """Get current beta value (annealed from beta_start to beta_end)."""
        fraction = min(self.frame / self.beta_frames, 1.0)
        return self.beta_start + fraction * (self.beta_end - self.beta_start)
