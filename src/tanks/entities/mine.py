"""Mine entity (future feature)."""

from .entity import Entity


class Mine(Entity):
    """Proximity mine (Phase 6 feature)."""

    def __init__(self, x, y, owner_id):
        super().__init__(x, y)
        self.owner_id = owner_id
        self.radius = 10
        self.trigger_radius = 50
        self.armed = False
        self.arm_delay = 1.0  # Seconds before mine arms

    def update(self, dt):
        """Update mine state."""
        if not self.armed:
            self.arm_delay -= dt
            if self.arm_delay <= 0:
                self.armed = True

    def check_trigger(self, entities):
        """Check if any entity triggers the mine."""
        if not self.armed:
            return None

        for entity in entities:
            if hasattr(entity, "owner_id") and entity.owner_id == self.owner_id:
                continue  # Don't trigger on owner

            dx = entity.x - self.x
            dy = entity.y - self.y
            dist_sq = dx * dx + dy * dy

            if dist_sq < self.trigger_radius * self.trigger_radius:
                return entity

        return None
