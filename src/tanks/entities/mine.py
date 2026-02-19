"""Mine entity - deployable explosive."""

from ..config.constants import MINE_DAMAGE, MINE_RADIUS, MINE_TRIGGER_RADIUS
from .entity import Entity


class Mine(Entity):
    """Proximity mine that detonates on enemy proximity or impact."""

    def __init__(self, x, y, owner_id):
        super().__init__(x, y)
        self.owner_id = owner_id
        self.radius = MINE_RADIUS
        self.trigger_radius = MINE_TRIGGER_RADIUS
        self.damage = MINE_DAMAGE
        self.armed = False
        self.arm_delay = 1.0  # Seconds before mine arms (prevents triggering on placer)

    def update(self, dt):
        """Update mine state (arm after delay).

        Args:
            dt: Delta time in seconds.

        """
        if not self.armed:
            self.arm_delay -= dt
            if self.arm_delay <= 0:
                self.armed = True

    def check_proximity(self, x, y) -> bool:
        """Check if a point is within trigger radius.

        Args:
            x: X coordinate to check.
            y: Y coordinate to check.

        Returns:
            True if armed and point is within trigger radius.

        """
        if not self.armed:
            return False

        dx = x - self.x
        dy = y - self.y
        distance = (dx * dx + dy * dy) ** 0.5
        return distance < self.trigger_radius

    def trigger(self):
        """Detonate the mine."""
        if self.armed:
            self.destroy()
