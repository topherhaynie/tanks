"""2D Vector class for physics calculations."""

from __future__ import annotations

import math


class Vector2:
    """Simple 2D vector class for physics calculations."""

    def __init__(self, x: float = 0, y: float = 0) -> None:
        """Initialize a 2D vector.

        Args:
            x: X component
            y: Y component

        """
        self.x = x
        self.y = y

    def __add__(self, other: Vector2) -> Vector2:
        """Add two vectors."""
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        """Subtract two vectors."""
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        """Multiply vector by scalar."""
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        """Divide vector by scalar."""
        return Vector2(self.x / scalar, self.y / scalar)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Vector2({self.x:.2f}, {self.y:.2f})"

    def length(self) -> float:
        """Calculate the length (magnitude) of the vector.

        Returns:
            Length of the vector

        """
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        """Calculate squared length (faster, for comparisons).

        Returns:
            Squared length of the vector

        """
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vector2:
        """Return a normalized (unit length) version of this vector.

        Returns:
            Normalized vector

        """
        length = self.length()
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)

    def dot(self, other: Vector2) -> float:
        """Calculate dot product with another vector.

        Args:
            other: Another vector

        Returns:
            Dot product

        """
        return self.x * other.x + self.y * other.y

    def rotate(self, angle_degrees: float) -> Vector2:
        """Rotate the vector by angle (in degrees).

        Args:
            angle_degrees: Rotation angle in degrees

        Returns:
            Rotated vector

        """
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        new_x = self.x * cos_a - self.y * sin_a
        new_y = self.x * sin_a + self.y * cos_a

        return Vector2(new_x, new_y)

    @staticmethod
    def from_angle(angle_degrees: float, length: float = 1) -> Vector2:
        """Create a vector from an angle and length.

        Args:
            angle_degrees: Angle in degrees
            length: Length of the vector

        Returns:
            New vector

        """
        angle_rad = math.radians(angle_degrees)
        return Vector2(
            math.cos(angle_rad) * length,
            math.sin(angle_rad) * length,
        )

    def to_tuple(self) -> tuple[float, float]:
        """Convert to tuple (x, y).

        Returns:
            Tuple of (x, y)

        """
        return (self.x, self.y)

    def copy(self) -> Vector2:
        """Create a copy of this vector.

        Returns:
            Copy of this vector

        """
        return Vector2(self.x, self.y)
