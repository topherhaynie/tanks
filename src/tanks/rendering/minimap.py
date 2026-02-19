"""Minimap rendering helpers."""

import math
from typing import TYPE_CHECKING, Any

import pygame

from tanks.config.constants import (
    COLOR_MINIMAP_BACKGROUND,
    COLOR_MINIMAP_BORDER,
    COLOR_MINIMAP_RADAR_RANGE,
    COLOR_MINIMAP_TANK_ENEMY,
    COLOR_MINIMAP_TANK_FRIENDLY,
    COLOR_MINIMAP_VISION_RANGE,
    COLOR_MINIMAP_WALL,
    COLOR_RADAR_BLIP_MINE,
    COLOR_RADAR_BLIP_TANK,
    FOG_TILE_SIZE,
    MINIMAP_MIN_REVEALED_FOG_TILES,
    MINIMAP_PADDING,
    MINIMAP_SIZE,
    RADAR_BLIP_FADE_TIME,
    RADAR_RADIUS,
    TILE_SIZE,
    VISION_RADIUS,
)

if TYPE_CHECKING:
    from tanks.entities.tank import Tank
    from tanks.maps.map import Map


class MinimapRenderer:
    """Draw the minimap and its overlays."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize minimap renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render(self, game_state: Any, tank: "Tank", current_time: float) -> None:
        """Render minimap with radar overlay.

        Args:
            game_state: Current game state.
            tank: Tank from whose perspective to render.
            current_time: Timestamp for consistent radar timing this frame.

        """
        if not tank.active:
            return

        # Calculate minimap position and scale
        minimap_x = self._screen.get_width() - MINIMAP_SIZE - MINIMAP_PADDING
        minimap_y = self._screen.get_height() - MINIMAP_SIZE - MINIMAP_PADDING
        map_width_px = game_state.game_map.width * TILE_SIZE
        map_height_px = game_state.game_map.height * TILE_SIZE
        scale = MINIMAP_SIZE / max(map_width_px, map_height_px)

        # Calculate offsets to center the map on the minimap
        scaled_map_width = map_width_px * scale
        scaled_map_height = map_height_px * scale
        offset_x = (MINIMAP_SIZE - scaled_map_width) / 2
        offset_y = (MINIMAP_SIZE - scaled_map_height) / 2

        # Create minimap surface
        minimap = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA)
        minimap.fill(COLOR_MINIMAP_BACKGROUND)

        # Draw map elements (pass offsets to center content)
        self._draw_revealed_areas(minimap, tank, game_state.game_map, scale, offset_x, offset_y)
        self._draw_ranges(minimap, tank, scale, offset_x, offset_y)
        self._draw_tanks(minimap, game_state.tanks, tank, scale, offset_x, offset_y, current_time)
        self._draw_radar_blips(minimap, tank, scale, offset_x, offset_y, current_time)

        # Draw border and blit to screen
        pygame.draw.rect(minimap, COLOR_MINIMAP_BORDER, (0, 0, MINIMAP_SIZE, MINIMAP_SIZE), 2)
        self._screen.blit(minimap, (minimap_x, minimap_y))

    def _draw_revealed_areas(
        self,
        minimap: pygame.Surface,
        tank: "Tank",
        game_map: "Map",
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> None:
        """Draw revealed fog areas and walls on minimap.

        Args:
            minimap: Minimap surface to draw on.
            tank: Perspective tank with fog memory.
            game_map: Game map with wall tiles.
            scale: Scale factor for minimap.
            offset_x: X offset to center map on minimap.
            offset_y: Y offset to center map on minimap.

        """
        if not tank.fog_memory:
            return

        # Draw each revealed fog tile
        for fty in range(tank.fog_memory.fog_height):
            for ftx in range(tank.fog_memory.fog_width):
                if tank.fog_memory.is_revealed(ftx, fty):
                    # Convert fog tile to minimap coordinates
                    fog_x = ftx * FOG_TILE_SIZE
                    fog_y = fty * FOG_TILE_SIZE
                    mini_x = int(fog_x * scale + offset_x)
                    mini_y = int(fog_y * scale + offset_y)
                    mini_size = max(1, int(FOG_TILE_SIZE * scale))

                    # Draw revealed area as lighter background
                    revealed_color = (40, 40, 60, 100)
                    pygame.draw.rect(minimap, revealed_color, (mini_x, mini_y, mini_size, mini_size))

        # Draw walls in revealed areas
        for y in range(game_map.height):
            for x in range(game_map.width):
                tile_type = game_map.get_tile(x, y)
                if tile_type > 0:  # Wall tile
                    # Check if this wall tile is in a revealed area
                    # A 64px wall tile overlaps with 2x2 fog tiles of 32px each
                    # Check all 4 fog tiles under this wall and require at least 3 to be revealed
                    wall_left = x * TILE_SIZE
                    wall_top = y * TILE_SIZE

                    # Get the 4 fog tile coordinates
                    fog_tiles = [
                        (int(wall_left / FOG_TILE_SIZE), int(wall_top / FOG_TILE_SIZE)),
                        (
                            int((wall_left + TILE_SIZE - 1) / FOG_TILE_SIZE),
                            int(wall_top / FOG_TILE_SIZE),
                        ),
                        (
                            int(wall_left / FOG_TILE_SIZE),
                            int((wall_top + TILE_SIZE - 1) / FOG_TILE_SIZE),
                        ),
                        (
                            int((wall_left + TILE_SIZE - 1) / FOG_TILE_SIZE),
                            int((wall_top + TILE_SIZE - 1) / FOG_TILE_SIZE),
                        ),
                    ]

                    # Count how many fog tiles are revealed
                    revealed_count = sum(
                        1
                        for ftx, fty in fog_tiles
                        if 0 <= ftx < tank.fog_memory.fog_width
                        and 0 <= fty < tank.fog_memory.fog_height
                        and tank.fog_memory.is_revealed(ftx, fty)
                    )

                    # Only show wall if at least MIN_REVEALED_FOG_TILES of 4 fog tiles are revealed
                    if revealed_count >= MINIMAP_MIN_REVEALED_FOG_TILES:
                        # Draw wall on minimap
                        mini_x = int(x * TILE_SIZE * scale + offset_x)
                        mini_y = int(y * TILE_SIZE * scale + offset_y)
                        mini_size = max(1, int(TILE_SIZE * scale))
                        pygame.draw.rect(minimap, COLOR_MINIMAP_WALL, (mini_x, mini_y, mini_size, mini_size))

    def _draw_ranges(
        self,
        minimap: pygame.Surface,
        tank: "Tank",
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> None:
        """Draw radar and vision range circles on minimap.

        Args:
            minimap: Minimap surface to draw on.
            tank: Perspective tank.
            scale: Scale factor for minimap.
            offset_x: X offset to center map on minimap.
            offset_y: Y offset to center map on minimap.

        """
        tank_mini_x = int(tank.x * scale + offset_x)
        tank_mini_y = int(tank.y * scale + offset_y)

        # Draw radar range circle (actual detection radius for tactical accuracy)
        radar_mini_radius = int(RADAR_RADIUS * scale)
        pygame.draw.circle(minimap, COLOR_MINIMAP_RADAR_RANGE, (tank_mini_x, tank_mini_y), radar_mini_radius, 1)

        # Draw vision range circle
        vision_mini_radius = int(VISION_RADIUS * scale)
        pygame.draw.circle(minimap, COLOR_MINIMAP_VISION_RANGE, (tank_mini_x, tank_mini_y), vision_mini_radius, 1)

    def _draw_tanks(
        self,
        minimap: pygame.Surface,
        tanks: list["Tank"],
        perspective_tank: "Tank",
        scale: float,
        offset_x: float,
        offset_y: float,
        current_time: float,
    ) -> None:
        """Draw tanks on minimap.

        Args:
            minimap: Minimap surface to draw on.
            tanks: List of all tanks.
            perspective_tank: Tank from whose perspective to render.
            scale: Scale factor for minimap.
            offset_x: X offset to center map on minimap.
            offset_y: Y offset to center map on minimap.
            current_time: Timestamp for consistent radar timing this frame.

        """
        for other_tank in tanks:
            if not other_tank.active:
                continue

            other_mini_x = int(other_tank.x * scale + offset_x)
            other_mini_y = int(other_tank.y * scale + offset_y)

            if other_tank == perspective_tank:
                self._draw_perspective_tank(minimap, other_tank, other_mini_x, other_mini_y)
            elif other_tank.team == perspective_tank.team:
                pygame.draw.circle(minimap, COLOR_MINIMAP_TANK_FRIENDLY, (other_mini_x, other_mini_y), 3)
            elif other_tank in perspective_tank.visible_entities:
                # Fully visible - solid red square
                square_size = 6
                pygame.draw.rect(
                    minimap,
                    COLOR_MINIMAP_TANK_ENEMY,
                    (other_mini_x - square_size // 2, other_mini_y - square_size // 2, square_size, square_size),
                )
            else:
                # Check radar blips for this tank with fade
                latest_blip = None
                for blip_entity, timestamp, _angle, snap_x, snap_y, _entity_type in reversed(
                    perspective_tank.radar_blips,
                ):
                    if blip_entity == other_tank:
                        latest_blip = (timestamp, snap_x, snap_y)
                        break

                if latest_blip:
                    timestamp, snap_x, snap_y = latest_blip
                    # Calculate fade based on time since detection
                    age = current_time - timestamp
                    if age < RADAR_BLIP_FADE_TIME:
                        # Fade from 255 to 0 over RADAR_BLIP_FADE_TIME seconds
                        fade_progress = age / RADAR_BLIP_FADE_TIME
                        alpha = int(255 * (1.0 - fade_progress))

                        # Draw fading red square at snapshot position
                        square_size = 6
                        blip_mini_x = int(snap_x * scale + offset_x)
                        blip_mini_y = int(snap_y * scale + offset_y)
                        temp_surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
                        faded_color = (*COLOR_MINIMAP_TANK_ENEMY[:3], alpha)
                        pygame.draw.rect(
                            temp_surface,
                            faded_color,
                            (0, 0, square_size, square_size),
                        )
                        minimap.blit(
                            temp_surface,
                            (blip_mini_x - square_size // 2, blip_mini_y - square_size // 2),
                        )

    def _draw_perspective_tank(self, minimap: pygame.Surface, tank: "Tank", mini_x: int, mini_y: int) -> None:
        """Draw the perspective tank with heading indicator on minimap.

        Args:
            minimap: Minimap surface to draw on.
            tank: The perspective tank.
            mini_x: Tank X position on minimap.
            mini_y: Tank Y position on minimap.

        """
        tank_size = 5
        pygame.draw.circle(minimap, COLOR_MINIMAP_TANK_FRIENDLY, (mini_x, mini_y), tank_size)

        # Draw heading indicator
        angle_rad = math.radians(tank.turret_angle)
        end_x = int(mini_x + math.cos(angle_rad) * tank_size * 2)
        end_y = int(mini_y + math.sin(angle_rad) * tank_size * 2)
        pygame.draw.line(minimap, COLOR_MINIMAP_TANK_FRIENDLY, (mini_x, mini_y), (end_x, end_y), 2)

    def _draw_radar_blips(
        self,
        minimap: pygame.Surface,
        tank: "Tank",
        scale: float,
        offset_x: float,
        offset_y: float,
        current_time: float,
    ) -> None:
        """Draw radar-detected entities on minimap.

        Args:
            minimap: Minimap surface to draw on.
            tank: Perspective tank.
            scale: Scale factor for minimap.
            offset_x: X offset to center map on minimap.
            offset_y: Y offset to center map on minimap.
            current_time: Timestamp for consistent radar timing this frame.

        """
        for entity, timestamp, _angle, snap_x, snap_y, entity_type in tank.radar_blips:
            # Only show entities with active (non-expired) blips
            age = current_time - timestamp
            if age >= RADAR_BLIP_FADE_TIME:
                continue

            # Skip if entity is visible (already drawn elsewhere) or inactive
            if entity in tank.visible_entities or not entity.active:
                continue

            # Skip tanks (they're drawn in _draw_minimap_tanks with fade)
            if entity_type == "Tank":
                continue

            # Use snapshot position
            entity_mini_x = int(snap_x * scale + offset_x)
            entity_mini_y = int(snap_y * scale + offset_y)

            # Determine color by entity type (from snapshot)
            color = COLOR_RADAR_BLIP_MINE if entity_type == "Mine" else COLOR_RADAR_BLIP_TANK

            # Calculate fade
            fade_progress = age / RADAR_BLIP_FADE_TIME
            alpha = int(255 * (1.0 - fade_progress))

            # Draw fading dot
            pulse_scale = 1.0 + 0.2 * math.sin(tank.radar_sweep_angle * math.pi / 180 * 4)
            blip_size = int(2 * pulse_scale)

            # Create temporary surface for alpha blending
            temp_surface = pygame.Surface((blip_size * 2, blip_size * 2), pygame.SRCALPHA)
            faded_color = (*color[:3], alpha)
            pygame.draw.circle(temp_surface, faded_color, (blip_size, blip_size), blip_size)
            minimap.blit(temp_surface, (entity_mini_x - blip_size, entity_mini_y - blip_size))
