"""Base entity class for all game objects."""


class Entity:
    """Base class for all game entities."""

    _next_id = 0

    def __init__(self, x, y):
        self.id = Entity._next_id
        Entity._next_id += 1

        self.x = x
        self.y = y
        self.active = True

    def update(self, dt):
        """Update entity state. Override in subclasses."""

    def destroy(self):
        """Mark entity for removal."""
        self.active = False
