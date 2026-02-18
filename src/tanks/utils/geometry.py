"""Geometric collision and intersection utilities."""

import math

# Epsilon for floating point comparisons
EPSILON = 1e-10


def circle_circle_collision(
    x1: float,
    y1: float,
    r1: float,
    x2: float,
    y2: float,
    r2: float,
) -> bool:
    """Check if two circles collide.

    Args:
        x1: X coordinate of first circle center
        y1: Y coordinate of first circle center
        r1: Radius of first circle
        x2: X coordinate of second circle center
        y2: Y coordinate of second circle center
        r2: Radius of second circle

    Returns:
        True if circles collide, False otherwise

    """
    dist_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    return dist_sq < (r1 + r2) ** 2


def circle_point_collision(
    cx: float,
    cy: float,
    radius: float,
    px: float,
    py: float,
) -> bool:
    """Check if a point is inside a circle.

    Args:
        cx: X coordinate of circle center
        cy: Y coordinate of circle center
        radius: Circle radius
        px: X coordinate of point
        py: Y coordinate of point

    Returns:
        True if point is inside circle, False otherwise

    """
    dist_sq = (px - cx) ** 2 + (py - cy) ** 2
    return dist_sq < radius**2


def line_circle_intersection(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    cx: float,
    cy: float,
    radius: float,
) -> tuple[bool, tuple[float, float] | None]:
    """Check if a line segment intersects with a circle.

    Args:
        x1: X coordinate of line start
        y1: Y coordinate of line start
        x2: X coordinate of line end
        y2: Y coordinate of line end
        cx: X coordinate of circle center
        cy: Y coordinate of circle center
        radius: Circle radius

    Returns:
        Tuple of (collides, closest_point) where closest_point is (x, y) or None

    """
    # Vector from line start to circle center
    dx = x2 - x1
    dy = y2 - y1
    fx = x1 - cx
    fy = y1 - cy

    # Quadratic formula coefficients
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    c = (fx * fx + fy * fy) - radius * radius

    discriminant = b * b - 4 * a * c

    if discriminant < 0:
        return False, None

    # Calculate intersection points
    discriminant = math.sqrt(discriminant)
    t1 = (-b - discriminant) / (2 * a)
    t2 = (-b + discriminant) / (2 * a)

    # Check if intersection is within line segment
    if (0 <= t1 <= 1) or (0 <= t2 <= 1):
        t = min(t1, t2) if t1 >= 0 else t2
        t = max(0, min(1, t))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return True, (closest_x, closest_y)

    return False, None


def line_line_intersection(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    x4: float,
    y4: float,
) -> tuple[bool, tuple[float, float] | None]:
    """Check if two line segments intersect.

    Args:
        x1: X coordinate of first line start
        y1: Y coordinate of first line start
        x2: X coordinate of first line end
        y2: Y coordinate of first line end
        x3: X coordinate of second line start
        y3: Y coordinate of second line start
        x4: X coordinate of second line end
        y4: Y coordinate of second line end

    Returns:
        Tuple of (intersects, point) where point is (x, y) or None

    """
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if abs(denom) < EPSILON:
        return False, None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return True, (ix, iy)

    return False, None


def closest_point_on_line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    px: float,
    py: float,
) -> tuple[float, float]:
    """Find the closest point on a line segment to a given point.

    Args:
        x1: X coordinate of line start
        y1: Y coordinate of line start
        x2: X coordinate of line end
        y2: Y coordinate of line end
        px: X coordinate of query point
        py: Y coordinate of query point

    Returns:
        Tuple of (x, y) coordinates of closest point on line

    """
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return x1, y1

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))

    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    return closest_x, closest_y


def reflect_vector(
    vx: float,
    vy: float,
    nx: float,
    ny: float,
) -> tuple[float, float]:
    """Reflect a velocity vector off a surface normal.

    Args:
        vx: X component of velocity vector
        vy: Y component of velocity vector
        nx: X component of surface normal (should be unit length)
        ny: Y component of surface normal (should be unit length)

    Returns:
        Tuple of (rx, ry) reflected velocity components

    """
    dot = vx * nx + vy * ny
    rx = vx - 2 * dot * nx
    ry = vy - 2 * dot * ny
    return rx, ry
