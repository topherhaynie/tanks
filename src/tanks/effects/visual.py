"""Visual effects for the game."""

import math


class VisualEffect:
    """Base class for visual effects."""

    def __init__(self, x: float, y: float, duration: float) -> None:
        """Initialize a visual effect.

        Args:
            x: X position.
            y: Y position.
            duration: How long the effect lasts in seconds.

        """
        self.x = x
        self.y = y
        self.duration = duration
        self.elapsed = 0.0
        self.active = True

    def update(self, dt: float) -> None:
        """Update the effect.

        Args:
            dt: Time delta in seconds.

        """
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False

    def get_alpha(self) -> float:
        """Get the alpha (opacity) value based on elapsed time.

        Returns:
            Alpha value from 0.0 to 1.0.

        """
        if self.duration <= 0:
            return 1.0
        return 1.0 - (self.elapsed / self.duration)


class MuzzleFlash(VisualEffect):
    """Muzzle flash effect when shooting."""

    def __init__(self, x: float, y: float, angle: float, duration: float = 0.1) -> None:
        """Initialize a muzzle flash.

        Args:
            x: X position (at turret tip).
            y: Y position (at turret tip).
            angle: Angle of the shot in degrees.
            duration: How long the flash lasts.

        """
        super().__init__(x, y, duration)
        self.angle = angle
        self.max_radius = 15
        self.color = (255, 255, 200)  # Bright yellow-white

    def get_radius(self) -> float:
        """Get the current radius of the flash.

        Returns:
            Current radius in pixels.

        """
        # Flash starts large and shrinks
        return self.max_radius * self.get_alpha()

    def get_flash_points(self) -> list[tuple[float, float]]:
        """Get the points for drawing a star-shaped flash.

        Returns:
            List of (x, y) points for the flash shape.

        """
        points = []
        num_points = 6
        angle_rad = math.radians(self.angle)

        for i in range(num_points * 2):
            # Alternate between outer and inner points for star shape
            radius = self.get_radius() if i % 2 == 0 else self.get_radius() * 0.4
            point_angle = angle_rad + (i * math.pi / num_points)

            px = self.x + math.cos(point_angle) * radius
            py = self.y + math.sin(point_angle) * radius
            points.append((px, py))

        return points
