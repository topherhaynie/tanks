"""Base controller interface."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.core.game import Game
    from tanks.entities.tank import Tank


class Controller:
    """Base class for tank controllers (human or bot)."""

    def __init__(self, tank: "Tank", game: "Game") -> None:
        """Initialize the controller.

        Args:
            tank: Tank to control.
            game: Game instance.

        """
        self.tank = tank
        self.game = game

    def update(self, dt: float) -> None:
        """Update controller and apply inputs to tank.

        Args:
            dt: Time delta in seconds.

        """

    def get_actions(self) -> dict[str, bool]:
        """Get current actions from controller.

        Returns:
            Dict with keys: move_forward, move_backward, turn_left, turn_right, shoot.

        """
        return {
            "move_forward": False,
            "move_backward": False,
            "turn_left": False,
            "turn_right": False,
            "shoot": False,
        }
