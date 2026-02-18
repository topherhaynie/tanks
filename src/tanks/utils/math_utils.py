"""Math utility functions."""

import math


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between min and max.

    Args:
        value: The value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        The clamped value

    """
    return max(min_value, min(max_value, value))


def normalize_angle(angle: float) -> float:
    """Normalize angle to [-180, 180] degrees.

    Args:
        angle: Angle in degrees

    Returns:
        Normalized angle in range [-180, 180]

    """
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b.

    Args:
        a: Start value
        b: End value
        t: Interpolation factor (0.0 to 1.0)

    Returns:
        Interpolated value

    """
    return a + (b - a) * t


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points.

    Args:
        x1: X coordinate of first point
        y1: Y coordinate of first point
        x2: X coordinate of second point
        y2: Y coordinate of second point

    Returns:
        Distance between the points

    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def angle_between(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate angle in degrees from point 1 to point 2.

    Args:
        x1: X coordinate of first point
        y1: Y coordinate of first point
        x2: X coordinate of second point
        y2: Y coordinate of second point

    Returns:
        Angle in degrees

    """
    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def angle_difference(angle1: float, angle2: float) -> float:
    """Calculate the shortest angular difference between two angles.

    Args:
        angle1: First angle in degrees
        angle2: Second angle in degrees

    Returns:
        Shortest angular difference in degrees

    """
    return normalize_angle(angle2 - angle1)
