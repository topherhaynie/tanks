"""Base controller interface."""


class Controller:
    """Base class for tank controllers (human or bot)."""

    def __init__(self, tank, game):
        self.tank = tank
        self.game = game

    def update(self, dt):
        """Update controller and apply inputs to tank."""

    def get_actions(self):
        """Get current actions from controller.
        Returns dict with keys: move_forward, move_backward, turn_left, turn_right, shoot
        """
        return {
            "move_forward": False,
            "move_backward": False,
            "turn_left": False,
            "turn_right": False,
            "shoot": False,
        }
