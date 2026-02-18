"""Bullet entity."""

from ..config.constants import BULLET_DAMAGE, BULLET_LIFETIME, BULLET_RADIUS
from .entity import Entity


class Bullet(Entity):
    """Bullet projectile with ricochet capability."""

    def __init__(self, x, y, vx, vy, owner_id):
        super().__init__(x, y)

        self.vx = vx
        self.vy = vy
        self.radius = BULLET_RADIUS
        self.owner_id = owner_id
        self.damage = BULLET_DAMAGE

        self.lifetime = BULLET_LIFETIME
        self.bounces = 0

    def update(self, dt):
        """Update bullet position and lifetime."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt

        if self.lifetime <= 0:
            self.destroy()
