"""Utility functions and helpers."""

from .geometry import (
    circle_circle_collision,
    circle_point_collision,
    closest_point_on_line,
    line_circle_intersection,
    line_line_intersection,
    reflect_vector,
)
from .math_utils import (
    angle_between,
    angle_difference,
    clamp,
    distance,
    lerp,
    normalize_angle,
)

__all__ = [
    "angle_between",
    "angle_difference",
    "circle_circle_collision",
    "circle_point_collision",
    "clamp",
    "closest_point_on_line",
    "distance",
    "lerp",
    "line_circle_intersection",
    "line_line_intersection",
    "normalize_angle",
    "reflect_vector",
]
