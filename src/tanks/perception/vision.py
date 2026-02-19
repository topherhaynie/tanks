"""Vision and radar perception systems."""

import math
from typing import TYPE_CHECKING, Any

from tanks.config.constants import (
    ENTITY_VISION_RADIUS,
    FOG_TILE_SIZE,
    RADAR_JAMMING_RADIUS,
    RADAR_RADIUS,
    TILE_SIZE,
    VISION_RADIUS,
)

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

    def update_vision(
        self, tank: "Tank", all_entities: list["Entity"]
    ) -> list["Entity"]:
        """Update tank's visible entities based on line of sight and fog state.

        Entities are visible if:
        - Within VISION_RADIUS (150px) - active fog revelation range, OR
        - Within ENTITY_VISION_RADIUS (600px) AND path is clear of fog (all fog tiles revealed)
        - AND line of sight is clear (no walls)

        Fog acts as a vision blocker for extended range. Entities can hide in/behind fog.

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

            # Check if entity is within either vision radius
            within_active_vision = distance <= VISION_RADIUS
            within_extended_vision = distance <= ENTITY_VISION_RADIUS

            if not within_extended_vision:
                continue

            # Check line of sight (walls)
            if not self.has_line_of_sight(tank.x, tank.y, entity.x, entity.y):
                continue

            # Within active vision radius - always visible if line of sight is clear
            if within_active_vision:
                visible.append(entity)
                continue

            # Extended vision - check if fog is blocking
            if tank.fog_memory and self._has_fog_blocking(
                tank.x, tank.y, entity.x, entity.y, tank.fog_memory
            ):
                continue

            # Extended vision with clear path - visible
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

    def _has_fog_blocking(
        self, x1: float, y1: float, x2: float, y2: float, fog_memory: Any
    ) -> bool:
        """Check if unrevealed fog blocks the path between two points.

        Args:
            x1: Starting X position.
            y1: Starting Y position.
            x2: Target X position.
            y2: Target Y position.
            fog_memory: Fog memory to check tile states.

        Returns:
            True if fog is blocking, False if path is clear of fog.

        """
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return False

        # Normalize direction
        dx /= distance
        dy /= distance

        # Step size (check every fog tile)
        step_size = FOG_TILE_SIZE
        steps = int(distance / step_size)

        # Ray march from start to end, checking fog tiles
        for i in range(steps + 1):
            check_x = x1 + dx * i * step_size
            check_y = y1 + dy * i * step_size

            # Convert to fog tile coordinates
            ftx = int(check_x / FOG_TILE_SIZE)
            fty = int(check_y / FOG_TILE_SIZE)

            # Check if this fog tile is within bounds and unrevealed
            if (
                0 <= ftx < fog_memory.fog_width
                and 0 <= fty < fog_memory.fog_height
                and not fog_memory.is_revealed(ftx, fty)
            ):
                return True  # Fog is blocking

        return False  # No fog blocking

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
                if not (
                    0 <= target_ftx < tank.fog_memory.fog_width
                    and 0 <= target_fty < tank.fog_memory.fog_height
                ):
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
        """Check line of sight and reveal fog tiles along clear path only.

        Args:
            x1: Starting X position.
            y1: Starting Y position.
            x2: Target X position.
            y2: Target Y position.
            target_ftx: Target fog tile X.
            target_fty: Target fog tile Y.
            fog_memory: Fog memory to update.

        Returns:
            True if target has line of sight or is a visible wall tile.

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

        # Track which fog tiles we've already revealed to avoid duplicates
        revealed_tiles = set()

        # Ray march from start to end
        for i in range(steps + 1):
            check_x = x1 + dx * i * step_size
            check_y = y1 + dy * i * step_size

            # Convert to game tile coordinates for wall check
            tx = int(check_x / TILE_SIZE)
            ty = int(check_y / TILE_SIZE)

            # Check if this game tile blocks vision
            if self.game_map.is_solid(tx, ty):
                # Reveal fog tiles that are part of this wall tile and within vision radius
                # A 64px wall tile contains 2x2 fog tiles of 32px each
                wall_ftx_min = (tx * TILE_SIZE) // FOG_TILE_SIZE
                wall_ftx_max = ((tx + 1) * TILE_SIZE - 1) // FOG_TILE_SIZE
                wall_fty_min = (ty * TILE_SIZE) // FOG_TILE_SIZE
                wall_fty_max = ((ty + 1) * TILE_SIZE - 1) // FOG_TILE_SIZE

                # Reveal fog tiles that overlap with this wall, but only if within vision radius
                for wall_fty in range(wall_fty_min, wall_fty_max + 1):
                    for wall_ftx in range(wall_ftx_min, wall_ftx_max + 1):
                        if (
                            0 <= wall_ftx < fog_memory.fog_width
                            and 0 <= wall_fty < fog_memory.fog_height
                        ):
                            # Check if this fog tile's center is within vision radius
                            fog_center_x = (wall_ftx + 0.5) * FOG_TILE_SIZE
                            fog_center_y = (wall_fty + 0.5) * FOG_TILE_SIZE
                            dist_x = fog_center_x - x1
                            dist_y = fog_center_y - y1
                            dist = math.sqrt(dist_x * dist_x + dist_y * dist_y)

                            if dist <= VISION_RADIUS:
                                fog_memory.reveal_tile(wall_ftx, wall_fty)

                # Vision is blocked - check if target is part of this wall
                return (
                    wall_ftx_min <= target_ftx <= wall_ftx_max
                    and wall_fty_min <= target_fty <= wall_fty_max
                )

            # No wall at this position - reveal the fog tile here
            ftx = int(check_x / FOG_TILE_SIZE)
            fty = int(check_y / FOG_TILE_SIZE)
            if (
                0 <= ftx < fog_memory.fog_width
                and 0 <= fty < fog_memory.fog_height
                and (ftx, fty) not in revealed_tiles
            ):
                fog_memory.reveal_tile(ftx, fty)
                revealed_tiles.add((ftx, fty))

        # Clear line of sight to target
        return True


class RadarSystem:
    """Handles radar detection (not blocked by walls)."""

    def detect_entities(
        self, tank: "Tank", all_entities: list["Entity"]
    ) -> list[tuple["Entity", float, float]]:
        """Detect entities within radar range.

        Radar is not blocked by walls and only detects tanks and mines.
        Radar can be jammed by enemy tanks with active jamming.

        Args:
            tank: The tank using radar.
            all_entities: All entities in the game.

        Returns:
            List of tuples (entity, distance, angle_degrees) for detected entities.

        """
        # Check if tank's radar is being jammed
        is_jammed = False
        for entity in all_entities:
            entity_type = type(entity).__name__
            if (
                entity_type == "Tank"
                and entity != tank
                and entity.active
                and hasattr(entity, "team")
                and entity.team != tank.team
                and hasattr(entity, "jamming_active")
                and entity.jamming_active
            ):
                # Check if jammer is within jamming range
                dx = entity.x - tank.x
                dy = entity.y - tank.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= RADAR_JAMMING_RADIUS:
                    is_jammed = True
                    break

        # If jammed, return empty detections
        if is_jammed:
            return []

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
