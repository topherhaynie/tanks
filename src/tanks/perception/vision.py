"""Vision and radar perception systems."""

import math
from typing import TYPE_CHECKING, Any

from tanks.config.constants import FOG_TILE_SIZE, RADAR_RADIUS, TILE_SIZE, VISION_RADIUS

if TYPE_CHECKING:
    from tanks.entities.entity import Entity
    from tanks.entities.tank import Tank
    from tanks.maps.map import Map


class VisionSystem:
    """Handles line-of-sight vision with raycasting."""

    def __init__(self, game_map: "Map") -> None:
        """Initialize vision system.

        Args:
            game_map: The game map for collision checks.

        """
        self.game_map = game_map

    def update_vision(self, tank: "Tank", all_entities: list["Entity"]) -> list["Entity"]:
        """Update tank's visible entities based on line of sight and fog memory.

        Entities are visible if:
        - Within VISION_RADIUS and line of sight is clear, OR
        - In revealed terrain (from fog memory) and line of sight is clear

        Args:
            tank: The tank doing the looking.
            all_entities: All entities in the game (tanks, bullets, mines).

        Returns:
            List of entities visible to this tank.

        """
        visible = []

        for entity in all_entities:
            # Don't see self
            if entity == tank:
                continue

            # Skip inactive entities
            if not entity.active:
                continue

            # Check distance
            dx = entity.x - tank.x
            dy = entity.y - tank.y
            distance = math.sqrt(dx * dx + dy * dy)

            # Check if entity is within immediate vision radius
            within_vision = distance <= VISION_RADIUS

            # Check if entity is in revealed terrain (fog memory)
            in_revealed_terrain = False
            if tank.fog_memory:
                entity_ftx = int(entity.x / FOG_TILE_SIZE)
                entity_fty = int(entity.y / FOG_TILE_SIZE)
                in_revealed_terrain = tank.fog_memory.is_revealed(entity_ftx, entity_fty)

            # Entity is visible if in vision range OR in revealed terrain, AND has line of sight
            if (within_vision or in_revealed_terrain) and self.has_line_of_sight(tank.x, tank.y, entity.x, entity.y):
                visible.append(entity)

        return visible

    def has_line_of_sight(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if there's a clear line of sight between two points.

        Uses DDA (Digital Differential Analyzer) raycasting to check if
        the line intersects any walls.

        Args:
            x1: Starting X position.
            y1: Starting Y position.
            x2: Target X position.
            y2: Target Y position.

        Returns:
            True if line of sight is clear, False if blocked by walls.

        """
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return True

        # Normalize direction
        dx /= distance
        dy /= distance

        # Step size (check every half tile)
        step_size = TILE_SIZE / 2
        steps = int(distance / step_size)

        # Ray march from start to end
        for i in range(steps + 1):
            check_x = x1 + dx * i * step_size
            check_y = y1 + dy * i * step_size

            # Convert to tile coordinates
            tx = int(check_x / TILE_SIZE)
            ty = int(check_y / TILE_SIZE)

            # Check if this tile blocks vision
            if self.game_map.is_solid(tx, ty):
                return False

        return True

    def reveal_visible_terrain(self, tank: "Tank") -> None:
        """Reveal fog tiles visible from tank's position.

        Uses raycasting to reveal fog tiles within vision radius.
        Walls are revealed even though they block vision beyond themselves.

        Args:
            tank: The tank revealing terrain.

        """
        if not tank.fog_memory:
            return

        # Calculate vision radius in fog tiles
        vision_radius_fog_tiles = int(VISION_RADIUS / FOG_TILE_SIZE) + 1

        # Tank's fog tile position
        tank_ftx = int(tank.x / FOG_TILE_SIZE)
        tank_fty = int(tank.y / FOG_TILE_SIZE)

        # Check all fog tiles in circle around tank
        for dy in range(-vision_radius_fog_tiles, vision_radius_fog_tiles + 1):
            for dx in range(-vision_radius_fog_tiles, vision_radius_fog_tiles + 1):
                target_ftx = tank_ftx + dx
                target_fty = tank_fty + dy

                # Check if fog tile is in bounds
                if not (0 <= target_ftx < tank.fog_memory.fog_width and 0 <= target_fty < tank.fog_memory.fog_height):
                    continue

                # Check distance
                fog_tile_center_x = (target_ftx + 0.5) * FOG_TILE_SIZE
                fog_tile_center_y = (target_fty + 0.5) * FOG_TILE_SIZE
                dist_x = fog_tile_center_x - tank.x
                dist_y = fog_tile_center_y - tank.y
                distance = math.sqrt(dist_x * dist_x + dist_y * dist_y)

                if distance > VISION_RADIUS:
                    continue

                # Check line of sight - reveal fog tile if visible OR if it's a wall blocking vision
                if self._has_line_of_sight_reveal_walls(
                    tank.x,
                    tank.y,
                    fog_tile_center_x,
                    fog_tile_center_y,
                    target_ftx,
                    target_fty,
                    tank.fog_memory,
                ):
                    tank.fog_memory.reveal_tile(target_ftx, target_fty)

    def _has_line_of_sight_reveal_walls(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        target_ftx: int,
        target_fty: int,
        fog_memory: Any,
    ) -> bool:
        """Check line of sight and reveal wall tiles along the path.

        Args:
            x1: Starting X position.
            y1: Starting Y position.
            x2: Target X position.
            y2: Target Y position.
            target_ftx: Target fog tile X.
            target_fty: Target fog tile Y.
            fog_memory: Fog memory to update.

        Returns:
            True if target has line of sight or is the blocking wall.

        """
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return True

        # Normalize direction
        dx /= distance
        dy /= distance

        # Step size (check every quarter tile for better wall detection)
        step_size = TILE_SIZE / 4
        steps = int(distance / step_size)

        # Track fog tiles we've revealed along the path
        revealed_fog_tiles = set()

        # Ray march from start to end
        for i in range(steps + 1):
            check_x = x1 + dx * i * step_size
            check_y = y1 + dy * i * step_size

            # Reveal fog tile at current position along ray
            ftx = int(check_x / FOG_TILE_SIZE)
            fty = int(check_y / FOG_TILE_SIZE)
            if (
                0 <= ftx < fog_memory.fog_width
                and 0 <= fty < fog_memory.fog_height
                and (ftx, fty) not in revealed_fog_tiles
            ):
                fog_memory.reveal_tile(ftx, fty)
                revealed_fog_tiles.add((ftx, fty))

            # Convert to game tile coordinates for wall check
            tx = int(check_x / TILE_SIZE)
            ty = int(check_y / TILE_SIZE)

            # Check if this game tile blocks vision
            if self.game_map.is_solid(tx, ty):
                # Reveal all fog tiles that overlap with this wall tile
                # (a 64px wall tile contains 2x2 fog tiles of 32px each)
                self._reveal_wall_fog_tiles(tx, ty, fog_memory)

                # If the target fog tile overlaps with this wall, consider it visible
                wall_ftx_min = (tx * TILE_SIZE) // FOG_TILE_SIZE
                wall_ftx_max = ((tx + 1) * TILE_SIZE - 1) // FOG_TILE_SIZE
                wall_fty_min = (ty * TILE_SIZE) // FOG_TILE_SIZE
                wall_fty_max = ((ty + 1) * TILE_SIZE - 1) // FOG_TILE_SIZE

                return wall_ftx_min <= target_ftx <= wall_ftx_max and wall_fty_min <= target_fty <= wall_fty_max

        return True  # Clear line of sight

    def _reveal_wall_fog_tiles(self, tx: int, ty: int, fog_memory: Any) -> None:
        """Reveal all fog tiles that overlap with a wall tile.

        Args:
            tx: Wall tile X coordinate.
            ty: Wall tile Y coordinate.
            fog_memory: Fog memory to update.

        """
        # Calculate fog tile range that overlaps with this wall tile
        # A 64px wall tile contains 2x2 fog tiles of 32px each
        ftx_min = (tx * TILE_SIZE) // FOG_TILE_SIZE
        ftx_max = ((tx + 1) * TILE_SIZE - 1) // FOG_TILE_SIZE
        fty_min = (ty * TILE_SIZE) // FOG_TILE_SIZE
        fty_max = ((ty + 1) * TILE_SIZE - 1) // FOG_TILE_SIZE

        # Reveal all fog tiles that overlap with this wall
        for fty in range(fty_min, fty_max + 1):
            for ftx in range(ftx_min, ftx_max + 1):
                if 0 <= ftx < fog_memory.fog_width and 0 <= fty < fog_memory.fog_height:
                    fog_memory.reveal_tile(ftx, fty)


class RadarSystem:
    """Handles radar detection (not blocked by walls)."""

    def detect_entities(self, tank: "Tank", all_entities: list["Entity"]) -> list[tuple["Entity", float, float]]:
        """Detect entities within radar range.

        Radar is not blocked by walls and only detects tanks and mines.

        Args:
            tank: The tank using radar.
            all_entities: All entities in the game.

        Returns:
            List of tuples (entity, distance, angle_degrees) for detected entities.

        """
        detected = []

        for entity in all_entities:
            # Don't detect self
            if entity == tank:
                continue

            # Skip inactive entities
            if not entity.active:
                continue

            # Only detect tanks and mines (not bullets)
            # Check entity type name
            entity_type = type(entity).__name__
            if entity_type not in ["Tank", "Mine"]:
                continue

            # Check distance
            dx = entity.x - tank.x
            dy = entity.y - tank.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > RADAR_RADIUS:
                continue

            # Calculate angle
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)

            detected.append((entity, distance, angle_deg))

        return detected
