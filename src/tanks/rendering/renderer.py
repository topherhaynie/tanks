"""Main renderer coordinating all drawing."""

import math
import time
from typing import TYPE_CHECKING, Any

import pygame

from tanks.effects.visual import MuzzleFlash, VisualEffect

if TYPE_CHECKING:
    from tanks.entities.tank import Tank
    from tanks.maps.map import Map

from tanks.config.constants import (
    COLOR_BACKGROUND,
    COLOR_BULLET,
    COLOR_DEBUG_HITBOX,
    COLOR_FOG,
    COLOR_MINIMAP_BACKGROUND,
    COLOR_MINIMAP_BORDER,
    COLOR_MINIMAP_RADAR_RANGE,
    COLOR_MINIMAP_TANK_ENEMY,
    COLOR_MINIMAP_TANK_FRIENDLY,
    COLOR_MINIMAP_VISION_RANGE,
    COLOR_MINIMAP_WALL,
    COLOR_RADAR_BLIP_MINE,
    COLOR_RADAR_BLIP_TANK,
    COLOR_RADAR_JAMMING,
    COLOR_RADAR_OVERLAY,
    COLOR_RADAR_SWEEP,
    COLOR_RADAR_SWEEP_BAR,
    COLOR_TANK_ENEMY,
    COLOR_TANK_FRIENDLY,
    COLOR_VISION_OVERLAY,
    COLOR_WALL,
    FOG_GRADIENT_SCALE,
    FOG_TILE_SIZE,
    MINIMAP_MIN_REVEALED_FOG_TILES,
    MINIMAP_PADDING,
    MINIMAP_SIZE,
    RADAR_BLIP_FADE_TIME,
    RADAR_JAMMING_RADIUS,
    RADAR_RADIUS,
    RADAR_VISUAL_RADIUS,
    TILE_SIZE,
    TILE_WALL_DIAGONAL_NE,
    TILE_WALL_DIAGONAL_NW,
    TILE_WALL_HORIZONTAL,
    TILE_WALL_SOLID,
    TILE_WALL_VERTICAL,
    VISION_RADIUS,
)


class Renderer:
    """Handles all game rendering."""

    def __init__(self, screen: pygame.Surface, settings: Any) -> None:
        """Initialize renderer.

        Args:
            screen: Pygame surface to render to.
            settings: Game settings object.

        """
        self.screen = screen
        self.settings = settings
        self.font = None
        self.perspective_tank = None  # Tank from whose perspective to render fog
        self.fog_gradient_stamp = None  # Pre-rendered fog gradient for performance

        # Initialize font for debug text
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        # Pre-render fog gradient stamp
        self._create_fog_gradient_stamp()

    def render_frame(self, game_state: Any) -> None:
        """Render a complete frame.

        Args:
            game_state: Current game state to render.

        """
        # Clear screen
        self.screen.fill(COLOR_BACKGROUND)

        # Layer 1: Map
        self.render_map(game_state.game_map)

        # Layer 2: Entities (filtered by visibility if in fog mode)
        if self.perspective_tank:
            self.render_bullets_filtered(game_state.bullets, self.perspective_tank)
            self.render_tanks_filtered(game_state.tanks, self.perspective_tank)
        else:
            self.render_bullets(game_state.bullets)
            self.render_tanks(game_state.tanks)

        # Layer 2.5: Visual effects
        self.render_effects(game_state.effects)

        # Layer 2.7: Fog of war
        if self.perspective_tank and self.perspective_tank.fog_memory:
            self.render_fog_of_war(game_state.game_map, self.perspective_tank)

        current_time = time.time()

        # Layer 2.8: Radar blips (on top of fog since radar sees through walls)
        if self.perspective_tank and self.settings.show_radar_blips:
            self.render_radar_blips(self.perspective_tank, current_time)

        # Layer 2.85: Radar jamming effects
        if self.settings.show_radar_blips:
            self.render_jamming_effects(game_state.tanks)

        # Layer 2.9: Minimap with radar overlay
        if self.perspective_tank and self.settings.show_minimap:
            self.render_minimap(game_state, self.perspective_tank, current_time)

        # Layer 3: Debug overlays
        if self.settings.show_hitboxes:
            self.render_hitboxes(game_state)

        if self.settings.show_vision and self.perspective_tank:
            self.render_vision_debug(self.perspective_tank)

        if self.settings.show_fps:
            self.render_fps(game_state.fps)

        # Render jamming status for perspective tank
        if self.perspective_tank:
            self.render_jamming_status(self.perspective_tank)

        # Update display
        pygame.display.flip()

    def render_map(self, game_map: "Map") -> None:
        """Render the tile-based map.

        Args:
            game_map: Map object to render.

        """
        if not game_map:
            return

        for y in range(game_map.height):
            for x in range(game_map.width):
                tile_type = game_map.get_tile(x, y)

                if tile_type > 0:
                    self.render_tile(x, y, tile_type)

    def render_tile(self, tx: int, ty: int, tile_type: int) -> None:
        """Render a single tile.

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.
            tile_type: Type of tile to render.

        """
        x = tx * TILE_SIZE
        y = ty * TILE_SIZE

        if tile_type == TILE_WALL_HORIZONTAL:
            # Horizontal line
            pygame.draw.line(self.screen, COLOR_WALL, (x, y + TILE_SIZE // 2), (x + TILE_SIZE, y + TILE_SIZE // 2), 3)

        elif tile_type == TILE_WALL_VERTICAL:
            # Vertical line
            pygame.draw.line(self.screen, COLOR_WALL, (x + TILE_SIZE // 2, y), (x + TILE_SIZE // 2, y + TILE_SIZE), 3)

        elif tile_type == TILE_WALL_DIAGONAL_NE:
            # NE-SW diagonal
            pygame.draw.line(self.screen, COLOR_WALL, (x, y + TILE_SIZE), (x + TILE_SIZE, y), 3)

        elif tile_type == TILE_WALL_DIAGONAL_NW:
            # NW-SE diagonal
            pygame.draw.line(self.screen, COLOR_WALL, (x, y), (x + TILE_SIZE, y + TILE_SIZE), 3)

        elif tile_type == TILE_WALL_SOLID:
            # Solid block
            pygame.draw.rect(self.screen, COLOR_WALL, (x, y, TILE_SIZE, TILE_SIZE))

    def render_tanks(self, tanks: list) -> None:
        """Render all tanks.

        Args:
            tanks: List of tank entities to render.

        """
        for tank in tanks:
            if not tank.active:
                continue

            color = COLOR_TANK_FRIENDLY if tank.team == 0 else COLOR_TANK_ENEMY

            # Draw body (circle)
            pygame.draw.circle(self.screen, color, (int(tank.x), int(tank.y)), tank.radius)

            # Draw direction indicator on body
            angle_rad = math.radians(tank.angle)
            end_x = tank.x + math.cos(angle_rad) * tank.radius
            end_y = tank.y + math.sin(angle_rad) * tank.radius
            pygame.draw.line(self.screen, (255, 255, 255), (tank.x, tank.y), (end_x, end_y), 2)

            # Draw turret
            turret_angle_rad = math.radians(tank.turret_angle)
            turret_end_x = tank.x + math.cos(turret_angle_rad) * (tank.radius + 8)
            turret_end_y = tank.y + math.sin(turret_angle_rad) * (tank.radius + 8)
            pygame.draw.line(self.screen, (200, 200, 200), (tank.x, tank.y), (turret_end_x, turret_end_y), 4)

            # Draw HP bar
            self.render_hp_bar(tank)

    def render_tanks_filtered(self, tanks: list, perspective_tank: "Tank") -> None:
        """Render only visible tanks based on perspective tank's vision.

        Args:
            tanks: List of tank entities to render.
            perspective_tank: Tank whose perspective determines visibility.

        """
        for tank in tanks:
            if not tank.active:
                continue

            # Always render the perspective tank itself
            if tank == perspective_tank or tank in perspective_tank.visible_entities:
                color = COLOR_TANK_FRIENDLY if tank.team == 0 else COLOR_TANK_ENEMY

                # Draw body (circle)
                pygame.draw.circle(self.screen, color, (int(tank.x), int(tank.y)), tank.radius)

                # Draw direction indicator on body
                angle_rad = math.radians(tank.angle)
                end_x = tank.x + math.cos(angle_rad) * tank.radius
                end_y = tank.y + math.sin(angle_rad) * tank.radius
                pygame.draw.line(self.screen, (255, 255, 255), (tank.x, tank.y), (end_x, end_y), 2)

                # Draw turret
                turret_angle_rad = math.radians(tank.turret_angle)
                turret_end_x = tank.x + math.cos(turret_angle_rad) * (tank.radius + 8)
                turret_end_y = tank.y + math.sin(turret_angle_rad) * (tank.radius + 8)
                pygame.draw.line(self.screen, (200, 200, 200), (tank.x, tank.y), (turret_end_x, turret_end_y), 4)

                # Draw HP bar
                self.render_hp_bar(tank)

    def render_bullets(self, bullets: list) -> None:
        """Render all bullets.

        Args:
            bullets: List of bullet entities to render.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            pygame.draw.circle(self.screen, COLOR_BULLET, (int(bullet.x), int(bullet.y)), bullet.radius)

    def render_bullets_filtered(self, bullets: list, perspective_tank: "Tank") -> None:
        """Render only visible bullets based on perspective tank's vision.

        Args:
            bullets: List of bullet entities to render.
            perspective_tank: Tank whose perspective determines visibility.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            # Only render bullets in visible entities list
            if bullet in perspective_tank.visible_entities:
                pygame.draw.circle(self.screen, COLOR_BULLET, (int(bullet.x), int(bullet.y)), bullet.radius)

    def render_effects(self, effects: list[VisualEffect]) -> None:
        """Render visual effects.

        Args:
            effects: List of visual effects to render.

        """
        for effect in effects:
            if not effect.active:
                continue

            if isinstance(effect, MuzzleFlash):
                self.render_muzzle_flash(effect)

    def render_muzzle_flash(self, flash: MuzzleFlash) -> None:
        """Render a muzzle flash effect.

        Args:
            flash: Muzzle flash effect to render.

        """
        points = flash.get_flash_points()
        min_points_for_polygon = 3
        if len(points) >= min_points_for_polygon:
            # Get alpha-adjusted color
            alpha = flash.get_alpha()
            color = tuple(int(c * alpha) for c in flash.color)

            # Draw the star shape
            pygame.draw.polygon(self.screen, color, points)

    def render_hp_bar(self, tank: "Tank") -> None:
        """Render health bar above tank.

        Args:
            tank: Tank entity to render HP bar for.

        """
        bar_width = tank.radius * 2
        bar_height = 4
        bar_x = tank.x - bar_width / 2
        bar_y = tank.y - tank.radius - 10

        # Red background bar
        pygame.draw.rect(self.screen, (200, 50, 50), (bar_x, bar_y, bar_width, bar_height))

        # Green foreground bar
        hp_ratio = tank.hp / tank.max_hp
        pygame.draw.rect(self.screen, (50, 200, 50), (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def render_hitboxes(self, game_state: Any) -> None:
        """Render debug hitboxes.

        Args:
            game_state: Current game state.

        """
        # Tank hitboxes
        for tank in game_state.tanks:
            if tank.active:
                pygame.draw.circle(self.screen, COLOR_DEBUG_HITBOX, (int(tank.x), int(tank.y)), tank.radius, 1)

        # Bullet hitboxes
        for bullet in game_state.bullets:
            if bullet.active:
                pygame.draw.circle(self.screen, COLOR_DEBUG_HITBOX, (int(bullet.x), int(bullet.y)), bullet.radius, 1)

    def render_fps(self, fps: float) -> None:
        """Render FPS counter.

        Args:
            fps: Current frames per second.

        """
        fps_text = self.small_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
        self.screen.blit(fps_text, (10, 10))

    def render_jamming_status(self, tank: "Tank") -> None:
        """Render jamming cooldown status for perspective tank.

        Args:
            tank: Tank to show jamming status for.

        """
        if not tank.active or not hasattr(tank, "jamming_cooldown"):
            return

        y_offset = 30  # Below FPS counter

        if tank.jamming_active:
            # Show active jamming timer
            status_text = f"JAMMING: {tank.jamming_timer:.1f}s"
            color = (255, 100, 100)  # Red when active
        elif tank.jamming_cooldown > 0:
            # Show cooldown
            status_text = f"Jam Cooldown: {tank.jamming_cooldown:.1f}s"
            color = (150, 150, 150)  # Gray during cooldown
        else:
            # Show ready status
            status_text = "Jam Ready (J)"
            color = (100, 255, 100)  # Green when ready

        text_surface = self.small_font.render(status_text, True, color)
        self.screen.blit(text_surface, (10, y_offset))

    def _create_fog_gradient_stamp(self) -> None:
        """Pre-render a fog gradient stamp for performance."""
        # Create a gradient stamp for smoother fog edges
        stamp_radius = int(FOG_TILE_SIZE * FOG_GRADIENT_SCALE)  # Configurable gradient bleed
        stamp_size = stamp_radius * 2
        self.fog_gradient_stamp = pygame.Surface((stamp_size, stamp_size), pygame.SRCALPHA)

        # Draw concentric circles with decreasing alpha
        gradient_steps = 16
        for i in range(gradient_steps):
            progress = i / gradient_steps
            # Gradient extends from center to edge
            radius = int(stamp_radius * (1.0 - progress * 0.6))

            # Smooth alpha curve
            alpha = int(COLOR_FOG[3] * (progress**2))  # Quadratic for tighter falloff
            color = (COLOR_FOG[0], COLOR_FOG[1], COLOR_FOG[2], alpha)

            pygame.draw.circle(self.fog_gradient_stamp, color, (stamp_radius, stamp_radius), radius)

    def render_fog_of_war(self, game_map: "Map", tank: "Tank") -> None:
        """Render fog of war with smooth edges based on tank's terrain memory.

        Args:
            game_map: The game map.
            tank: Tank whose perspective to render from.

        """
        if not tank.fog_memory:
            return

        # Create a fog surface
        map_width_px = game_map.width * TILE_SIZE
        map_height_px = game_map.height * TILE_SIZE
        fog_surface = pygame.Surface((map_width_px, map_height_px), pygame.SRCALPHA)

        # First pass: Draw solid fog tiles for unrevealed areas
        for y in range(tank.fog_memory.fog_height):
            for x in range(tank.fog_memory.fog_width):
                if not tank.fog_memory.is_revealed(x, y):
                    fog_rect = pygame.Rect(x * FOG_TILE_SIZE, y * FOG_TILE_SIZE, FOG_TILE_SIZE, FOG_TILE_SIZE)
                    pygame.draw.rect(fog_surface, COLOR_FOG, fog_rect)

        # Second pass: Add smooth gradient at fog edges
        self._add_fog_gradients(fog_surface, tank.fog_memory)

        # Blit fog surface to screen
        self.screen.blit(fog_surface, (0, 0))

    def _add_fog_gradients(self, fog_surface: pygame.Surface, memory: Any) -> None:
        """Add smooth gradients at fog edges for revealed tiles.

        Args:
            fog_surface: Surface to draw gradients on.
            memory: Terrain memory to check tile states.

        """
        stamp_radius = self.fog_gradient_stamp.get_width() // 2

        # Only process revealed tiles that have unrevealed neighbors
        for y in range(memory.fog_height):
            for x in range(memory.fog_width):
                if memory.is_revealed(x, y) and self._has_fog_neighbor(memory, x, y):
                    # Stamp gradient centered on this tile
                    center_x = int((x + 0.5) * FOG_TILE_SIZE)
                    center_y = int((y + 0.5) * FOG_TILE_SIZE)

                    fog_surface.blit(
                        self.fog_gradient_stamp,
                        (center_x - stamp_radius, center_y - stamp_radius),
                        special_flags=pygame.BLEND_RGBA_MAX,
                    )

    def _has_fog_neighbor(self, memory: Any, x: int, y: int) -> bool:
        """Check if a tile has any unrevealed neighbors.

        Args:
            memory: Terrain memory to check.
            x: Fog tile X coordinate.
            y: Fog tile Y coordinate.

        Returns:
            True if any neighbor is unrevealed.

        """
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                if not memory.is_revealed(x + dx, y + dy):
                    return True
        return False

    def render_vision_debug(self, tank: "Tank") -> None:
        """Render debug visualization for vision and radar ranges.

        Args:
            tank: Tank to visualize vision for.

        """
        if not tank.active:
            return

        # Create a surface with per-pixel alpha for overlays
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Draw vision circle
        pygame.draw.circle(overlay, COLOR_VISION_OVERLAY, (int(tank.x), int(tank.y)), int(VISION_RADIUS))

        # Draw radar circle
        pygame.draw.circle(
            overlay,
            COLOR_RADAR_OVERLAY,
            (int(tank.x), int(tank.y)),
            int(RADAR_VISUAL_RADIUS),
            2,  # Width for outline
        )

        # Draw radar sweep line
        sweep_rad = math.radians(tank.radar_sweep_angle)
        sweep_end_x = tank.x + math.cos(sweep_rad) * RADAR_VISUAL_RADIUS
        sweep_end_y = tank.y + math.sin(sweep_rad) * RADAR_VISUAL_RADIUS
        pygame.draw.line(overlay, COLOR_RADAR_SWEEP, (tank.x, tank.y), (sweep_end_x, sweep_end_y), 2)

        # Blit overlay to screen
        self.screen.blit(overlay, (0, 0))

    def render_radar_blips(self, tank: "Tank", current_time: float) -> None:
        """Render radar sweep bar and fading blips for detected entities.

        Args:
            tank: Tank whose radar to render.
            current_time: Timestamp for consistent radar timing this frame.

        """
        if not tank.active or not hasattr(tank, "radar_sweep_angle"):
            return

        # Create overlay surface
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Draw rotating green sweep line (counter-clockwise)
        sweep_angle_rad = math.radians(tank.radar_sweep_angle)
        sweep_end_x = tank.x + math.cos(sweep_angle_rad) * RADAR_VISUAL_RADIUS
        sweep_end_y = tank.y + math.sin(sweep_angle_rad) * RADAR_VISUAL_RADIUS
        pygame.draw.line(overlay, COLOR_RADAR_SWEEP_BAR, (tank.x, tank.y), (sweep_end_x, sweep_end_y), 2)

        # Draw fading blips for detected entities
        if hasattr(tank, "radar_blips"):
            for entity, blip_time, _angle, snap_x, snap_y, entity_type in tank.radar_blips:
                if not entity.active:
                    continue

                # Calculate fade based on time
                age = current_time - blip_time
                if age >= RADAR_BLIP_FADE_TIME:
                    continue

                fade_ratio = 1.0 - (age / RADAR_BLIP_FADE_TIME)

                # Determine color based on entity type (from snapshot)
                base_color = COLOR_RADAR_BLIP_MINE if entity_type == "Mine" else COLOR_RADAR_BLIP_TANK

                # Apply fade to alpha
                blip_alpha = int(base_color[3] * fade_ratio)
                blip_color = (base_color[0], base_color[1], base_color[2], blip_alpha)

                # Draw pulsing blip
                pulse = 1.0 + 0.2 * math.sin(current_time * 10)  # Fast pulse
                blip_size = int(10 * fade_ratio * pulse)

                # Draw outer ring at snapshot position
                pygame.draw.circle(
                    overlay,
                    blip_color,
                    (int(snap_x), int(snap_y)),
                    blip_size + 3,
                    2,
                )

                # Draw inner filled circle
                inner_alpha = int(blip_alpha * 0.6)
                inner_color = (base_color[0], base_color[1], base_color[2], inner_alpha)
                pygame.draw.circle(
                    overlay,
                    inner_color,
                    (int(snap_x), int(snap_y)),
                    blip_size,
                )

        # Blit overlay to screen
        self.screen.blit(overlay, (0, 0))

    def render_jamming_effects(self, tanks: list["Tank"]) -> None:
        """Render radar jamming visual effects.

        Args:
            tanks: List of all tanks to check for active jamming.

        """
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        for tank in tanks:
            if not tank.active:
                continue

            # Check if tank has jamming active
            if hasattr(tank, "jamming_active") and tank.jamming_active:
                # Draw pulsing jamming effect circle
                pulse_scale = 1.0 + 0.2 * math.sin(tank.radar_sweep_angle * math.pi / 180 * 6)
                jamming_radius = int(RADAR_JAMMING_RADIUS * pulse_scale)

                # Draw multiple concentric circles for wave effect
                for i in range(3):
                    radius_offset = i * 30
                    alpha = max(0, int(COLOR_RADAR_JAMMING[3] * (1.0 - i * 0.3)))
                    color = (COLOR_RADAR_JAMMING[0], COLOR_RADAR_JAMMING[1], COLOR_RADAR_JAMMING[2], alpha)
                    pygame.draw.circle(
                        overlay,
                        color,
                        (int(tank.x), int(tank.y)),
                        jamming_radius - radius_offset,
                        2,
                    )

                # Draw "JAMMING" text above tank
                jam_text = "JAMMING"
                text_surface = self.small_font.render(jam_text, True, (255, 100, 100))
                text_bg = pygame.Surface((text_surface.get_width() + 4, text_surface.get_height() + 2), pygame.SRCALPHA)
                text_bg.fill((0, 0, 0, 180))

                text_x = int(tank.x) - text_surface.get_width() // 2
                text_y = int(tank.y) - tank.radius - 30

                overlay.blit(text_bg, (text_x - 2, text_y - 1))
                overlay.blit(text_surface, (text_x, text_y))

        self.screen.blit(overlay, (0, 0))

    def render_minimap(self, game_state: Any, tank: "Tank", current_time: float) -> None:
        """Render minimap with radar overlay.

        Args:
            game_state: Current game state.
            tank: Tank from whose perspective to render.
            current_time: Timestamp for consistent radar timing this frame.

        """
        if not tank.active:
            return

        # Calculate minimap position and scale
        minimap_x = self.screen.get_width() - MINIMAP_SIZE - MINIMAP_PADDING
        minimap_y = self.screen.get_height() - MINIMAP_SIZE - MINIMAP_PADDING
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
        self._draw_minimap_revealed_areas(minimap, tank, game_state.game_map, scale, offset_x, offset_y)
        self._draw_minimap_ranges(minimap, tank, scale, offset_x, offset_y)
        self._draw_minimap_tanks(minimap, game_state.tanks, tank, scale, offset_x, offset_y, current_time)
        self._draw_minimap_radar_blips(minimap, tank, scale, offset_x, offset_y, current_time)

        # Draw border and blit to screen
        pygame.draw.rect(minimap, COLOR_MINIMAP_BORDER, (0, 0, MINIMAP_SIZE, MINIMAP_SIZE), 2)
        self.screen.blit(minimap, (minimap_x, minimap_y))

    def _draw_minimap_revealed_areas(
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
                    revealed_color = (40, 40, 60, 100)  # Slightly lighter than background
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

    def _draw_minimap_ranges(
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

    def _draw_minimap_tanks(
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
                self._draw_perspective_tank_on_minimap(minimap, other_tank, other_mini_x, other_mini_y)
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
                for entity, timestamp, _angle, snap_x, snap_y, _entity_type in perspective_tank.radar_blips:
                    if entity == other_tank:
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
                        break

    def _draw_perspective_tank_on_minimap(
        self,
        minimap: pygame.Surface,
        tank: "Tank",
        mini_x: int,
        mini_y: int,
    ) -> None:
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

    def _draw_minimap_radar_blips(
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

    def set_perspective_tank(self, tank: "Tank | None") -> None:
        """Set which tank's perspective to render fog from.

        Args:
            tank: Tank to render perspective from, or None for no fog.

        """
        self.perspective_tank = tank
