"""Missile entity - fast projectile with no ricochet."""

from ..config.constants import MISSILE_DAMAGE, MISSILE_LIFETIME, MISSILE_RADIUS
from .entity import Entity


class Missile(Entity):
    """Missile projectile with high speed and no bounce."""

    def __init__(self, x, y, vx, vy, owner_id):
        super().__init__(x, y)

        self.vx = vx
        self.vy = vy
        self.radius = MISSILE_RADIUS
        self.owner_id = owner_id
        self.damage = MISSILE_DAMAGE

        self.lifetime = MISSILE_LIFETIME

        # Track previous position for swept collision detection
        self.prev_x = x
        self.prev_y = y

    def update(self, dt):
        """Update missile position and lifetime.

        Args:
            dt: Delta time in seconds.

        """
        # Store previous position
        self.prev_x = self.x
        self.prev_y = self.y

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt

        if self.lifetime <= 0:
            self.destroy()
