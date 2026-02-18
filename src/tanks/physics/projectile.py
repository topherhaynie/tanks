"""Projectile physics including ricochet."""

import math
from typing import TYPE_CHECKING

from tanks.config.constants import BULLET_SPEED, MAX_BULLET_BOUNCES
from tanks.utils.geometry import reflect_vector

if TYPE_CHECKING:
    from tanks.entities.entity import Entity


class ProjectileSystem:
    """Handles bullet movement and ricochet."""

    @staticmethod
    def update_bullet(bullet: "Entity", dt: float) -> None:
        """Update bullet position.

        Args:
            bullet: Bullet entity to update.
            dt: Time delta in seconds.

        """
        bullet.x += bullet.vx * dt
        bullet.y += bullet.vy * dt
        bullet.lifetime -= dt

    @staticmethod
    def create_bullet(x: float, y: float, angle: float, owner_id: int) -> dict:
        """Create a bullet with velocity based on angle.

        Args:
            x: Initial X position.
            y: Initial Y position.
            angle: Firing angle in degrees.
            owner_id: ID of tank that fired the bullet.

        Returns:
            Dictionary containing bullet data.

        """
        angle_rad = math.radians(angle)
        vx = math.cos(angle_rad) * BULLET_SPEED
        vy = math.sin(angle_rad) * BULLET_SPEED

        return {
            "x": x,
            "y": y,
            "vx": vx,
            "vy": vy,
            "angle": angle,
            "owner_id": owner_id,
            "bounces": 0,
        }

    @staticmethod
    def bounce_bullet(bullet: "Entity", normal_x: float, normal_y: float) -> bool:
        """Bounce bullet off a surface with given normal.

        Args:
            bullet: Bullet entity to bounce.
            normal_x: X component of surface normal.
            normal_y: Y component of surface normal.

        Returns:
            True if bounce succeeded, False if bullet should be destroyed.

        """
        if bullet.bounces >= MAX_BULLET_BOUNCES:
            return False

        # Reflect velocity vector
        new_vx, new_vy = reflect_vector(bullet.vx, bullet.vy, normal_x, normal_y)

        bullet.vx = new_vx
        bullet.vy = new_vy
        bullet.angle = math.degrees(math.atan2(new_vy, new_vx))
        bullet.bounces += 1

        return True
