"""Camera system for view management."""


class Camera:
    """Camera for scrolling view (future feature for larger maps)."""

    def __init__(self, width, height):
        self.x = 0
        self.y = 0
        self.width = width
        self.height = height

    def center_on(self, x, y):
        """Center camera on world coordinates."""
        self.x = x - self.width / 2
        self.y = y - self.height / 2

    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates."""
        return x - self.x, y - self.y

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        return sx + self.x, sy + self.y
