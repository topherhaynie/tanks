"""RLBot: Bot wrapper for trained RL agents.

This module provides a Bot implementation that wraps trained RL agents
(DQN, PPO, etc.) so they can be used anywhere a Bot is expected:
- Tournament matches
- Demo modes
- Arena battles
- Mixed human/bot gameplay

The wrapper handles encoding BotState into state vectors and decoding
action indices back to BotActions.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from tanks.bots.bot_api import BotAction, BotState
from tanks.rl.state import StateEncoder

if TYPE_CHECKING:
    from tanks.rl.actions import DiscreteActionSpace
    from tanks.rl.models.agent import Agent


class RLBot:
    """Bot wrapper for RL agents.

    Implements the Bot protocol (update method) by wrapping a trained RL agent.
    Handles state encoding and action decoding internally.

    Usage:
        # Load trained agent
        from tanks.rl.models.dqn import DQNAgent
        agent = DQNAgent.load("checkpoints/best_dqn.pt")

        # Wrap as bot
        bot = RLBot(agent)

        # Use like any other bot
        game.add_input_handler(BotController(tank, game, bot))
    """

    def __init__(
        self,
        agent: "Agent",
        state_encoder: StateEncoder | None = None,
        action_space: "DiscreteActionSpace | None" = None,
        deterministic: bool = True,
    ) -> None:
        """Initialize RLBot wrapper.

        Args:
            agent: Trained RL agent (DQN, PPO, etc.).
            state_encoder: State encoder for converting BotState to vectors.
                          If None, creates default encoder.
            action_space: Action space for converting action indices to BotActions.
                         If None, creates default discrete action space.
            deterministic: If True, agent always takes best action.
                          If False, agent samples from policy (exploration).

        """
        # Lazy import to avoid circular dependency
        from tanks.rl.actions import DiscreteActionSpace as DiscreteActionSpaceImpl

        self.agent = agent
        self.state_encoder = state_encoder or StateEncoder()
        self.action_space = action_space or DiscreteActionSpaceImpl()
        self.deterministic = deterministic

    def update(self, state: BotState) -> BotAction:
        """Compute bot action from current state.

        This is the main Bot protocol method. It:
        1. Encodes BotState into state vector (78 floats)
        2. Queries agent for action index
        3. Converts action index to BotAction

        Args:
            state: Bot state snapshot from game.

        Returns:
            BotAction describing desired inputs.

        """
        # Encode state to vector
        state_vector = self.state_encoder.encode(state)

        # Get action from agent
        action_index = self.agent.predict(state_vector, self.deterministic)

        # Convert to bot action
        bot_action = self.action_space.to_bot_action(action_index)

        return bot_action

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        agent_class: type["Agent"],
        deterministic: bool = True,
    ) -> "RLBot":
        """Load RLBot from checkpoint file.

        Args:
            checkpoint_path: Path to agent checkpoint.
            agent_class: Agent class (DQNAgent, PPOAgent, etc.).
            deterministic: Whether to use deterministic actions.

        Returns:
            RLBot instance with loaded agent.

        Raises:
            FileNotFoundError: If checkpoint doesn't exist.

        """
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.exists():
            msg = f"Checkpoint not found: {checkpoint_path}"
            raise FileNotFoundError(msg)

        # Load agent from checkpoint
        agent = agent_class.load(str(checkpoint_path))

        return cls(agent, deterministic=deterministic)

    def __repr__(self) -> str:
        """String representation."""
        agent_name = self.agent.__class__.__name__
        mode = "deterministic" if self.deterministic else "stochastic"
        return f"RLBot({agent_name}, {mode})"
