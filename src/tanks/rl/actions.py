"""Action space definitions for reinforcement learning.

Defines discrete and continuous action spaces for RL agents, and conversion
between action space representations and BotAction commands.
"""

from abc import ABC, abstractmethod
from enum import IntEnum

import numpy as np

from tanks.bots.bot_api import BotAction


class DiscreteAction(IntEnum):
    """Discrete action enumeration for DQN."""

    NOOP = 0
    MOVE_FORWARD = 1
    MOVE_BACKWARD = 2
    TURN_LEFT = 3
    TURN_RIGHT = 4
    MOVE_FORWARD_TURN_LEFT = 5
    MOVE_FORWARD_TURN_RIGHT = 6
    MOVE_BACKWARD_TURN_LEFT = 7
    MOVE_BACKWARD_TURN_RIGHT = 8
    SHOOT = 9
    FIRE_MISSILE = 10
    PLACE_MINE = 11


class ActionSpace(ABC):
    """Abstract base class for action spaces."""

    @abstractmethod
    def sample(self) -> int | np.ndarray:
        """Sample a random action from the space.

        Returns:
            Action representation (int for discrete, array for continuous).

        """

    @abstractmethod
    def to_bot_action(self, action: int | np.ndarray) -> BotAction:
        """Convert action to BotAction.

        Args:
            action: Action representation from agent.

        Returns:
            BotAction for game system.

        """

    @abstractmethod
    def get_size(self) -> int:
        """Get the size/dimension of action space.

        Returns:
            Number of discrete actions or continuous dimensions.

        """


class DiscreteActionSpace(ActionSpace):
    """Discrete action space for DQN agents.

    12 discrete actions:
    0: NOOP - No action
    1: MOVE_FORWARD - Move forward
    2: MOVE_BACKWARD - Move backward
    3: TURN_LEFT - Turn left
    4: TURN_RIGHT - Turn right
    5: MOVE_FORWARD + TURN_LEFT - Move forward while turning left
    6: MOVE_FORWARD + TURN_RIGHT - Move forward while turning right
    7: MOVE_BACKWARD + TURN_LEFT - Move backward while turning left
    8: MOVE_BACKWARD + TURN_RIGHT - Move backward while turning right
    9: SHOOT - Fire bullet
    10: FIRE_MISSILE - Fire missile
    11: PLACE_MINE - Place mine
    """

    def __init__(self, auto_aim: bool = True) -> None:
        """Initialize discrete action space.

        Args:
            auto_aim: If True, turret automatically aims at nearest enemy.
                     If False, agent must control turret manually (more actions).

        """
        self.auto_aim = auto_aim
        self.num_actions = 12  # Fixed for now

    def sample(self) -> int:
        """Sample a random action."""
        return int(np.random.randint(0, self.num_actions))

    def to_bot_action(self, action: int | np.ndarray) -> BotAction:
        """Convert discrete action to BotAction.

        Args:
            action: Integer action index [0, 11].

        Returns:
            BotAction with appropriate flags set.

        """
        # Handle numpy integers
        if isinstance(action, np.ndarray):
            action = int(action.item())
        else:
            action = int(action)
        action_enum = DiscreteAction(action)

        # Initialize all flags to False
        move_forward = False
        move_backward = False
        turn_left = False
        turn_right = False
        shoot = False
        fire_missile = False
        place_mine = False

        # Set flags based on action
        if action_enum == DiscreteAction.NOOP:
            pass  # All flags stay False

        elif action_enum == DiscreteAction.MOVE_FORWARD:
            move_forward = True

        elif action_enum == DiscreteAction.MOVE_BACKWARD:
            move_backward = True

        elif action_enum == DiscreteAction.TURN_LEFT:
            turn_left = True

        elif action_enum == DiscreteAction.TURN_RIGHT:
            turn_right = True

        elif action_enum == DiscreteAction.MOVE_FORWARD_TURN_LEFT:
            move_forward = True
            turn_left = True

        elif action_enum == DiscreteAction.MOVE_FORWARD_TURN_RIGHT:
            move_forward = True
            turn_right = True

        elif action_enum == DiscreteAction.MOVE_BACKWARD_TURN_LEFT:
            move_backward = True
            turn_left = True

        elif action_enum == DiscreteAction.MOVE_BACKWARD_TURN_RIGHT:
            move_backward = True
            turn_right = True

        elif action_enum == DiscreteAction.SHOOT:
            shoot = True

        elif action_enum == DiscreteAction.FIRE_MISSILE:
            fire_missile = True

        elif action_enum == DiscreteAction.PLACE_MINE:
            place_mine = True

        return BotAction(
            move_forward=move_forward,
            move_backward=move_backward,
            turn_left=turn_left,
            turn_right=turn_right,
            turret_left=False,  # Controlled by auto-aim or separate agent
            turret_right=False,
            shoot=shoot,
            fire_missile=fire_missile,
            place_mine=place_mine,
            desired_turret_angle=None,  # Auto-aim will set this if enabled
        )

    def get_size(self) -> int:
        """Get number of discrete actions."""
        return self.num_actions


class ContinuousActionSpace(ActionSpace):
    """Continuous action space for PPO agents.

    4 continuous values:
    - move_speed: [-1.0, 1.0] where -1=full backward, 0=stop, 1=full forward
    - turn_rate: [-1.0, 1.0] where -1=full left, 0=straight, 1=full right
    - turret_angle_delta: [-1.0, 1.0] relative turret rotation
    - shoot_confidence: [0.0, 1.0] threshold for firing (>0.5=shoot, >0.8=missile)

    Additional discrete actions derived from thresholds:
    - shoot: shoot_confidence > 0.5
    - fire_missile: shoot_confidence > 0.8 and missile ready
    - place_mine: shoot_confidence > 0.9 and mine ready
    """

    def __init__(self, auto_aim: bool = True) -> None:
        """Initialize continuous action space.

        Args:
            auto_aim: If True, turret auto-aim is handled by environment.

        """
        self.num_dimensions = 4
        self.auto_aim = auto_aim

    def sample(self) -> np.ndarray:
        """Sample a random continuous action."""
        return np.random.uniform(-1.0, 1.0, size=4).astype(np.float32)

    def to_bot_action(self, action: np.ndarray) -> BotAction:
        """Convert continuous action to BotAction.

        Args:
            action: Numpy array of shape (4,) with values in [-1, 1] or [0, 1].

        Returns:
            BotAction with appropriate flags and continuous values.

        """
        move_speed = float(np.clip(action[0], -1.0, 1.0))
        turn_rate = float(np.clip(action[1], -1.0, 1.0))
        turret_delta = float(np.clip(action[2], -1.0, 1.0))
        shoot_signal = float(np.clip(action[3], -1.0, 1.0))
        shoot_confidence = (shoot_signal + 1.0) * 0.5

        # Convert continuous values to discrete flags
        move_forward = move_speed > 0.1
        move_backward = move_speed < -0.1
        turn_left = turn_rate < -0.1
        turn_right = turn_rate > 0.1
        turret_left = (turret_delta < -0.1) and not self.auto_aim
        turret_right = (turret_delta > 0.1) and not self.auto_aim

        # Shooting thresholds
        shoot = shoot_confidence > 0.5
        fire_missile = shoot_confidence > 0.8
        place_mine = shoot_confidence > 0.9

        return BotAction(
            move_forward=move_forward,
            move_backward=move_backward,
            turn_left=turn_left,
            turn_right=turn_right,
            turret_left=turret_left,
            turret_right=turret_right,
            shoot=shoot,
            fire_missile=fire_missile,
            place_mine=place_mine,
            desired_turret_angle=None,  # Could use turret_delta for relative control
        )

    def get_size(self) -> int:
        """Get number of continuous dimensions."""
        return self.num_dimensions


def create_discrete_action_space(auto_aim: bool = True) -> DiscreteActionSpace:
    """Create discrete action space for DQN agents.

    Args:
        auto_aim: Whether turret should auto-aim at enemies.

    Returns:
        DiscreteActionSpace instance.

    """
    return DiscreteActionSpace(auto_aim=auto_aim)


def create_continuous_action_space() -> ContinuousActionSpace:
    """Create continuous action space for PPO agents.

    Returns:
        ContinuousActionSpace instance.

    """
    return ContinuousActionSpace()
