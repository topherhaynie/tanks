"""Collision detection and resolution system."""

import math

from ..config.constants import TILE_SIZE
from ..utils.geometry import (
    circle_circle_collision,
    closest_point_on_line,
    line_circle_intersection,
)


class CollisionSystem:
    """Handles collision detection and resolution."""

    def __init__(self, game_map):
        self.map = game_map

    def check_tank_wall_collision(self, tank, map_tiles):
        """Check and resolve tank-wall collisions with sliding.

        Returns True if collision occurred.
        Only processes active tanks.

        """
        # Skip collision if tank is inactive
        if not tank.active:
            return False

        collided = False

        # Get nearby tiles (optimization)
        tiles_to_check = self._get_nearby_tiles(tank.x, tank.y, tank.radius)

        for tile in tiles_to_check:
            if self._resolve_circle_tile_collision(tank, tile):
                collided = True

        return collided

    def check_tank_tank_collision(self, tank1, tank2):
        """Check and resolve tank-tank collision.

        Pushes tanks apart if overlapping.
        Only collides if both tanks are active.

        """
        # Skip collision if either tank is inactive
        if not tank1.active or not tank2.active:
            return False

        dx = tank2.x - tank1.x
        dy = tank2.y - tank1.y
        dist = math.sqrt(dx * dx + dy * dy)
        min_dist = tank1.radius + tank2.radius

        if dist < min_dist and dist > 0:
            # Push apart
            overlap = min_dist - dist
            push_x = (dx / dist) * overlap * 0.5
            push_y = (dy / dist) * overlap * 0.5

            tank1.x -= push_x
            tank1.y -= push_y
            tank2.x += push_x
            tank2.y += push_y

            return True

        return False

    def check_bullet_wall_collision(self, bullet):
        """Check if bullet hits a wall using swept collision detection.

        Returns (hit, normal) tuple where normal is the wall surface normal.
        Uses continuous collision detection to prevent tunneling.

        """
        from ..utils.geometry import line_line_intersection

        # Check tiles along bullet's path
        tiles_current = self._get_nearby_tiles(bullet.x, bullet.y, bullet.radius)
        tiles_prev = self._get_nearby_tiles(bullet.prev_x, bullet.prev_y, bullet.radius)
        tiles_to_check = list(set(tiles_current + tiles_prev))

        # Find all collisions with their time of impact
        collisions = []

        for tile in tiles_to_check:
            tx, ty, tile_type = tile
            edges = self._get_tile_edges(tx, ty, tile_type)

            for edge in edges:
                x1, y1, x2, y2 = edge

                # Method 1: Check if bullet's movement path crosses the edge (swept)
                hit_swept = False
                t_impact = 1.0
                swept_point = None

                # Only do swept check if bullet moved significantly
                move_dist_sq = (bullet.x - bullet.prev_x) ** 2 + (
                    bullet.y - bullet.prev_y
                ) ** 2
                if move_dist_sq > 0.01:
                    hit_swept, swept_point = line_line_intersection(
                        bullet.prev_x,
                        bullet.prev_y,
                        bullet.x,
                        bullet.y,
                        x1,
                        y1,
                        x2,
                        y2,
                    )

                    if hit_swept and swept_point:
                        # Calculate time of impact along bullet's path
                        dx = bullet.x - bullet.prev_x
                        dy = bullet.y - bullet.prev_y
                        t_dx = swept_point[0] - bullet.prev_x
                        t_dy = swept_point[1] - bullet.prev_y
                        t_impact = (t_dx * dx + t_dy * dy) / move_dist_sq
                        t_impact = max(0, min(1, t_impact))

                # Method 2: Check if current bullet position intersects edge (circle-line)
                hit_circle, circle_point = line_circle_intersection(
                    x1,
                    y1,
                    x2,
                    y2,
                    bullet.x,
                    bullet.y,
                    bullet.radius,
                )

                # Use whichever collision occurred first (swept has priority)
                hit = hit_swept or hit_circle
                collision_point = swept_point if hit_swept else circle_point

                if hit and collision_point:
                    # Calculate edge normal
                    edge_dx = x2 - x1
                    edge_dy = y2 - y1
                    length = math.sqrt(edge_dx * edge_dx + edge_dy * edge_dy)

                    if length > 0:
                        # Normal perpendicular to edge
                        normal_x = -edge_dy / length
                        normal_y = edge_dx / length

                        # Ensure normal points toward bullet
                        to_bullet_x = bullet.x - collision_point[0]
                        to_bullet_y = bullet.y - collision_point[1]
                        if normal_x * to_bullet_x + normal_y * to_bullet_y < 0:
                            normal_x = -normal_x
                            normal_y = -normal_y

                        # Only count if bullet is moving toward this edge
                        approach_speed = -(bullet.vx * normal_x + bullet.vy * normal_y)
                        if approach_speed > 0.001:  # Small threshold for floating point
                            # Use time of impact for swept, distance for circle
                            priority = t_impact if hit_swept else 1.0
                            collisions.append((priority, (normal_x, normal_y)))

        # Return the earliest collision
        if collisions:
            collisions.sort(key=lambda c: c[0])
            return True, collisions[0][1]

        return False, None

    def check_bullet_tank_collision(self, bullet, tanks):
        """Check if bullet hits any tank.

        Returns the tank that was hit, or None.

        """
        for tank in tanks:
            # Skip inactive or friendly fire
            if not tank.active or tank.id == bullet.owner_id:
                continue

            if circle_circle_collision(
                bullet.x,
                bullet.y,
                bullet.radius,
                tank.x,
                tank.y,
                tank.radius,
            ):
                return tank

        return None

    def _get_nearby_tiles(self, x, y, radius):
        """Get tiles near a position (for optimized collision checking)."""
        if not self.map:
            return []

        # Calculate tile range
        min_tile_x = int((x - radius) // TILE_SIZE)
        max_tile_x = int((x + radius) // TILE_SIZE)
        min_tile_y = int((y - radius) // TILE_SIZE)
        max_tile_y = int((y + radius) // TILE_SIZE)

        tiles = []
        for ty in range(min_tile_y, max_tile_y + 1):
            for tx in range(min_tile_x, max_tile_x + 1):
                tile_type = self.map.get_tile(tx, ty)
                if tile_type > 0:  # Non-empty tile
                    tiles.append((tx, ty, tile_type))

        return tiles

    def _resolve_circle_tile_collision(self, entity, tile_info):
        """Resolve collision between circular entity and a tile."""
        tx, ty, tile_type = tile_info

        # Get tile edges based on type
        edges = self._get_tile_edges(tx, ty, tile_type)

        collided = False
        for edge in edges:
            x1, y1, x2, y2 = edge

            # Find closest point on edge
            closest_x, closest_y = closest_point_on_line(
                x1,
                y1,
                x2,
                y2,
                entity.x,
                entity.y,
            )

            # Check distance
            dx = entity.x - closest_x
            dy = entity.y - closest_y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < entity.radius:
                # Push entity away
                if dist > 0:
                    push_x = (dx / dist) * (entity.radius - dist)
                    push_y = (dy / dist) * (entity.radius - dist)
                    entity.x += push_x
                    entity.y += push_y
                    collided = True

        return collided

    def _get_tile_edges(self, tx, ty, tile_type):
        """Get edge line segments for a tile based on its type."""
        from ..config.constants import (
            TILE_WALL_DIAGONAL_NE,
            TILE_WALL_DIAGONAL_NW,
            TILE_WALL_HORIZONTAL,
            TILE_WALL_SOLID,
            TILE_WALL_VERTICAL,
        )

        x = tx * TILE_SIZE
        y = ty * TILE_SIZE
        size = TILE_SIZE

        if tile_type == TILE_WALL_HORIZONTAL:
            # Horizontal wall across middle
            return [(x, y + size / 2, x + size, y + size / 2)]

        if tile_type == TILE_WALL_VERTICAL:
            # Vertical wall across middle
            return [(x + size / 2, y, x + size / 2, y + size)]

        if tile_type == TILE_WALL_DIAGONAL_NE:
            # NE-SW diagonal
            return [(x, y + size, x + size, y)]

        if tile_type == TILE_WALL_DIAGONAL_NW:
            # NW-SE diagonal
            return [(x, y, x + size, y + size)]

        if tile_type == TILE_WALL_SOLID:
            # All four edges
            return [
                (x, y, x + size, y),  # Top
                (x + size, y, x + size, y + size),  # Right
                (x + size, y + size, x, y + size),  # Bottom
                (x, y + size, x, y),  # Left
            ]

        return []
