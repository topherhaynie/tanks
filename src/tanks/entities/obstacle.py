"""Obstacle/wall entity."""

from .entity import Entity


class Obstacle(Entity):
    """Static obstacle or wall segment."""

    def __init__(self, x, y, width, height):
        super().__init__(x, y)
        self.width = width
        self.height = height

    def get_bounds(self):
        """Get bounding box."""
        return (self.x, self.y, self.width, self.height)
