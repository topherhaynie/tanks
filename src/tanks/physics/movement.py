"""Tank movement system."""

import math
from typing import TYPE_CHECKING

from tanks.config.constants import TANK_MAX_SPEED, TANK_TURN_RATE, TURRET_TURN_RATE
from tanks.utils.math_utils import angle_difference, normalize_angle

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class MovementSystem:
    """Handles tank movement and rotation."""

    @staticmethod
    def update_tank_movement(
        tank: "Tank",
        move_forward: bool,
        move_backward: bool,
        turn_left: bool,
        turn_right: bool,
        dt: float,
    ) -> None:
        """Update tank position and rotation based on inputs.

        Uses arcade-style movement (no acceleration).

        Args:
            tank: Tank entity to update.
            move_forward: Whether moving forward.
            move_backward: Whether moving backward.
            turn_left: Whether turning left.
            turn_right: Whether turning right.
            dt: Time delta in seconds.

        """
        # Rotation (pygame Y-axis points down, so signs are swapped)
        if turn_left:
            tank.angle -= TANK_TURN_RATE * dt
        if turn_right:
            tank.angle += TANK_TURN_RATE * dt

        tank.angle = normalize_angle(tank.angle)

        # Movement
        speed = 0
        if move_forward:
            speed = TANK_MAX_SPEED
        elif move_backward:
            speed = -TANK_MAX_SPEED * 0.6  # Slower reverse

        if speed != 0:
            angle_rad = math.radians(tank.angle)
            tank.x += math.cos(angle_rad) * speed * dt
            tank.y += math.sin(angle_rad) * speed * dt

    @staticmethod
    def update_turret_rotation(tank: "Tank", target_angle: float, dt: float) -> None:
        """Rotate turret toward target angle.

        Target angle is relative to the tank's body angle.

        Args:
            tank: Tank entity to update.
            target_angle: Target angle in degrees.
            dt: Time delta in seconds.

        """
        # Calculate difference between current and target
        diff = angle_difference(tank.turret_angle, target_angle)

        # Rotate toward target at max turn rate
        max_rotation = TURRET_TURN_RATE * dt

        if abs(diff) <= max_rotation:
            tank.turret_angle = target_angle
        else:
            tank.turret_angle += max_rotation if diff > 0 else -max_rotation

        tank.turret_angle = normalize_angle(tank.turret_angle)

    @staticmethod
    def update_turret_aim(tank: "Tank", world_x: float, world_y: float) -> float:
        """Point turret at world coordinates.

        Args:
            tank: Tank entity to update.
            world_x: Target world X coordinate.
            world_y: Target world Y coordinate.

        Returns:
            The absolute angle the turret should face in degrees.

        """
        dx = world_x - tank.x
        dy = world_y - tank.y

        if dx == 0 and dy == 0:
            return tank.turret_angle

        target_angle = math.degrees(math.atan2(dy, dx))
        return normalize_angle(target_angle)
