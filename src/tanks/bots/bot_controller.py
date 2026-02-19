"""Controller implementation that drives a tank from a bot."""

import math
from typing import TYPE_CHECKING

from tanks.bots.bot_api import Bot, BotAction
from tanks.bots.sensors import build_bot_state
from tanks.config.constants import TURRET_TURN_RATE
from tanks.input.controller import Controller
from tanks.physics.movement import MovementSystem
from tanks.utils.math_utils import normalize_angle

if TYPE_CHECKING:
    from tanks.core.game import Game
    from tanks.entities.tank import Tank


class BotController(Controller):
    """Controller that applies bot actions to a tank."""

    def __init__(self, tank: "Tank", game: "Game", bot: Bot) -> None:
        """Create a bot controller.

        Args:
            tank: Tank to control.
            game: Game instance.
            bot: Bot implementation.

        """
        super().__init__(tank, game)
        self._bot = bot
        self._last_action = BotAction()

    def update(self, dt: float) -> None:
        """Update the bot and apply its actions.

        Args:
            dt: Time delta in seconds.

        """
        if not self.tank.active:
            return

        tick_id = self.game.input_tick_id
        state = build_bot_state(self.tank, self.game, tick_id, dt)
        action = self._bot.update(state) or BotAction()
        self._last_action = action

        MovementSystem.update_tank_movement(
            self.tank,
            action.move_forward,
            action.move_backward,
            action.turn_left,
            action.turn_right,
            dt,
        )

        self._apply_turret_action(action, dt)

        if action.shoot:
            self.game.shoot_bullet(self.tank)

        if action.fire_missile:
            self.game.fire_missile(self.tank)

        if action.place_mine:
            self.game.place_mine(self.tank)

    def _apply_turret_action(self, action: BotAction, dt: float) -> None:
        if action.desired_turret_angle is not None:
            target_degrees = math.degrees(action.desired_turret_angle)
            MovementSystem.update_turret_rotation(self.tank, target_degrees, dt)
            return

        if action.turret_left:
            self.tank.turret_angle += TURRET_TURN_RATE * dt
        if action.turret_right:
            self.tank.turret_angle -= TURRET_TURN_RATE * dt

        self.tank.turret_angle = normalize_angle(self.tank.turret_angle)
