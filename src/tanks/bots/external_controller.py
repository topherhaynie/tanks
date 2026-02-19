"""External bot controller integrating external bots with the input system."""

import math
from typing import TYPE_CHECKING

from tanks.bots.external_runner import BotCrashError, ExternalBotRunner
from tanks.bots.sensors import build_bot_state
from tanks.config.constants import TURRET_TURN_RATE
from tanks.input.controller import Controller
from tanks.physics.movement import MovementSystem
from tanks.utils.math_utils import normalize_angle

if TYPE_CHECKING:
    from tanks.core.game import Game
    from tanks.entities.tank import Tank


class ExternalBotController(Controller):
    """Controller wrapper for external bot processes.

    Integrates external bot runner (subprocess) with the game's input system.
    Sends BotState via JSON, receives BotAction, updates tank inputs.

    Attributes:
        runner: ExternalBotRunner managing subprocess communication.
        tick_id: Current input tick counter.

    """

    def __init__(self, tank: "Tank", game: "Game", runner: ExternalBotRunner) -> None:
        """Initialize external bot controller.

        Args:
            tank: Tank to control.
            game: Game instance.
            runner: ExternalBotRunner instance (should be started).

        """
        super().__init__(tank, game)
        self.runner = runner
        self.tick_id = 0

    def update(self, dt: float) -> None:
        """Update tank inputs from external bot.

        Args:
            dt: Delta time since last update.

        """
        if not self.tank.active:
            return

        self.tick_id += 1

        # Build bot state snapshot
        state = build_bot_state(self.tank, self.game, self.tick_id, dt)

        # Get action from external bot
        try:
            action = self.runner.update(state)
        except BotCrashError:
            # Bot crashed - stop movement
            return

        # Apply movement actions via MovementSystem
        MovementSystem.update_tank_movement(
            self.tank,
            action.move_forward,
            action.move_backward,
            action.turn_left,
            action.turn_right,
            dt,
        )

        # Apply turret actions
        if action.desired_turret_angle is not None:
            # Use absolute angle (converted from radians to degrees)
            target_degrees = math.degrees(action.desired_turret_angle)
            MovementSystem.update_turret_rotation(self.tank, target_degrees, dt)
        else:
            # Use discrete rotation
            if action.turret_left:
                self.tank.turret_angle += TURRET_TURN_RATE * dt
            if action.turret_right:
                self.tank.turret_angle -= TURRET_TURN_RATE * dt
            self.tank.turret_angle = normalize_angle(self.tank.turret_angle)

        # Handle shooting
        if action.shoot:
            self.game.shoot_bullet(self.tank)
