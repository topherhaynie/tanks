"""Keyboard controller for human players."""

from typing import TYPE_CHECKING

import pygame

from tanks.input.controller import Controller
from tanks.physics.movement import MovementSystem

if TYPE_CHECKING:
    from tanks.core.game import Game
    from tanks.entities.tank import Tank


class KeyboardController(Controller):
    """Keyboard-based tank controller."""

    def __init__(
        self, tank: "Tank", game: "Game", key_bindings: dict[str, int] | None = None
    ) -> None:
        """Create a keyboard controller.

        Args:
            tank: Tank to control.
            game: Game instance.
            key_bindings: Dict mapping action names to pygame keys.

        """
        super().__init__(tank, game)

        # Default WASD + Space controls
        if key_bindings is None:
            key_bindings = {
                "move_forward": pygame.K_w,
                "move_backward": pygame.K_s,
                "turn_left": pygame.K_a,
                "turn_right": pygame.K_d,
                "shoot": pygame.K_SPACE,
                "jam": pygame.K_j,
            }

        self.key_bindings = key_bindings
        self.jam_key_was_pressed = False  # Track jam key state for single activation

    def update(self, dt: float) -> None:
        """Update tank based on keyboard input.

        Args:
            dt: Time delta in seconds.

        """
        if not self.tank.active:
            return

        keys = pygame.key.get_pressed()

        # Movement
        move_forward = keys[self.key_bindings["move_forward"]]
        move_backward = keys[self.key_bindings["move_backward"]]
        turn_left = keys[self.key_bindings["turn_left"]]
        turn_right = keys[self.key_bindings["turn_right"]]

        MovementSystem.update_tank_movement(
            self.tank,
            move_forward,
            move_backward,
            turn_left,
            turn_right,
            dt,
        )

        # Turret aiming (follow mouse)
        mouse_x, mouse_y = pygame.mouse.get_pos()
        target_angle = MovementSystem.update_turret_aim(self.tank, mouse_x, mouse_y)
        MovementSystem.update_turret_rotation(self.tank, target_angle, dt)

        # Shooting
        if keys[self.key_bindings["shoot"]]:
            self.game.shoot_bullet(self.tank)

        # Radar jamming (single activation on key press)
        jam_key_pressed = keys[self.key_bindings["jam"]]
        if (
            jam_key_pressed
            and not self.jam_key_was_pressed
            and hasattr(self.tank, "activate_jamming")
        ):
            self.tank.activate_jamming()
        self.jam_key_was_pressed = jam_key_pressed


class KeyboardController2(Controller):
    """Second keyboard controller for player 2 (arrow keys + RCtrl)."""

    def __init__(self, tank: "Tank", game: "Game") -> None:
        """Create keyboard controller for player 2.

        Args:
            tank: Tank to control.
            game: Game instance.

        """
        super().__init__(tank, game)

        self.key_bindings = {
            "move_forward": pygame.K_UP,
            "move_backward": pygame.K_DOWN,
            "turn_left": pygame.K_LEFT,
            "turn_right": pygame.K_RIGHT,
            "shoot": pygame.K_RCTRL,
            "jam": pygame.K_RSHIFT,
        }

        self.aim_angle = 0
        self.jam_key_was_pressed = False  # Track jam key state for single activation

    def update(self, dt: float) -> None:
        """Update tank based on keyboard input.

        Args:
            dt: Time delta in seconds.

        """
        if not self.tank.active:
            return

        keys = pygame.key.get_pressed()

        # Movement
        move_forward = keys[self.key_bindings["move_forward"]]
        move_backward = keys[self.key_bindings["move_backward"]]
        turn_left = keys[self.key_bindings["turn_left"]]
        turn_right = keys[self.key_bindings["turn_right"]]

        MovementSystem.update_tank_movement(
            self.tank,
            move_forward,
            move_backward,
            turn_left,
            turn_right,
            dt,
        )

        # Turret aiming (IJKL keys for rotation)
        if keys[pygame.K_j]:
            self.aim_angle += 180 * dt
        if keys[pygame.K_l]:
            self.aim_angle -= 180 * dt

        self.tank.turret_angle = self.aim_angle

        # Shooting
        if keys[self.key_bindings["shoot"]]:
            self.game.shoot_bullet(self.tank)

        # Radar jamming (single activation on key press)
        jam_key_pressed = keys[self.key_bindings["jam"]]
        if (
            jam_key_pressed
            and not self.jam_key_was_pressed
            and hasattr(self.tank, "activate_jamming")
        ):
            self.tank.activate_jamming()
        self.jam_key_was_pressed = jam_key_pressed
