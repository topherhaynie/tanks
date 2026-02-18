"""Main renderer coordinating all drawing."""

import math
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
    COLOR_RADAR_BLIP,
    COLOR_RADAR_OVERLAY,
    COLOR_RADAR_SWEEP,
    COLOR_TANK_ENEMY,
    COLOR_TANK_FRIENDLY,
    COLOR_VISION_OVERLAY,
    COLOR_WALL,
    FOG_TILE_SIZE,
    RADAR_RADIUS,
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
        self.radar_sweep_angle = 0.0  # Current angle of radar sweep animation
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

        # Layer 2.8: Radar blips (on top of fog since radar sees through walls)
        if self.perspective_tank and self.settings.show_radar_blips:
            self.render_radar_blips(self.perspective_tank)

        # Update radar sweep animation
        radar_sweep_degrees_per_second = 180
        self.radar_sweep_angle += radar_sweep_degrees_per_second * (1.0 / 60.0)  # At 60fps
        full_circle_degrees = 360
        if self.radar_sweep_angle >= full_circle_degrees:
            self.radar_sweep_angle -= full_circle_degrees

        # Layer 3: Debug overlays
        if self.settings.show_hitboxes:
            self.render_hitboxes(game_state)

        if self.settings.show_vision and self.perspective_tank:
            self.render_vision_debug(self.perspective_tank)

        if self.settings.show_fps:
            self.render_fps(game_state.fps)

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

    def _create_fog_gradient_stamp(self) -> None:
        """Pre-render a fog gradient stamp for performance."""
        # Create a larger circular gradient stamp for smoother blending
        stamp_radius = int(FOG_TILE_SIZE * 2.0)  # Increased from 1.5x to 2.0x
        stamp_size = stamp_radius * 2
        self.fog_gradient_stamp = pygame.Surface((stamp_size, stamp_size), pygame.SRCALPHA)

        # Draw concentric circles with smoother decreasing alpha
        gradient_steps = 20  # Increased from 16 for smoother gradient
        for i in range(gradient_steps):
            progress = i / gradient_steps
            # Adjusted falloff curve for smoother blending
            radius = int(stamp_radius * (1.0 - progress * 0.5))  # Less aggressive falloff

            # Smooth alpha curve with exponential falloff
            alpha = int(COLOR_FOG[3] * (progress**1.5))  # Exponential makes it smoother
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
            int(RADAR_RADIUS),
            2,  # Width for outline
        )

        # Draw radar sweep line
        sweep_rad = math.radians(self.radar_sweep_angle)
        sweep_end_x = tank.x + math.cos(sweep_rad) * RADAR_RADIUS
        sweep_end_y = tank.y + math.sin(sweep_rad) * RADAR_RADIUS
        pygame.draw.line(overlay, COLOR_RADAR_SWEEP, (tank.x, tank.y), (sweep_end_x, sweep_end_y), 2)

        # Blit overlay to screen
        self.screen.blit(overlay, (0, 0))

    def render_radar_blips(self, tank: "Tank") -> None:
        """Render radar detection blips for entities detected by radar.

        Args:
            tank: Tank whose radar detections to render.

        """
        if not tank.active or not hasattr(tank, "radar_detections"):
            return

        # Create overlay surface
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Render each radar detection
        for entity, distance, _angle_deg in tank.radar_detections:
            # Skip if entity is already visible (don't need radar blip)
            if entity in tank.visible_entities:
                continue

            # Calculate blip size based on distance (closer = larger)
            max_blip_size = 12
            min_blip_size = 4
            distance_ratio = min(distance / RADAR_RADIUS, 1.0)
            blip_size = int(max_blip_size - (max_blip_size - min_blip_size) * distance_ratio)

            # Draw pulsing radar blip
            pulse_scale = 1.0 + 0.3 * math.sin(self.radar_sweep_angle * math.pi / 180 * 4)
            current_blip_size = int(blip_size * pulse_scale)

            # Draw outer ring (pulse effect)
            pygame.draw.circle(
                overlay,
                COLOR_RADAR_BLIP,
                (int(entity.x), int(entity.y)),
                current_blip_size + 3,
                2,
            )

            # Draw inner filled circle with varying alpha
            inner_alpha = max(0, min(255, int(200 * (2.0 - pulse_scale))))
            inner_color = (COLOR_RADAR_BLIP[0], COLOR_RADAR_BLIP[1], COLOR_RADAR_BLIP[2], inner_alpha)
            pygame.draw.circle(
                overlay,
                inner_color,
                (int(entity.x), int(entity.y)),
                current_blip_size,
            )

            # Draw directional line from perspective tank to blip
            line_alpha = 80
            line_color = (COLOR_RADAR_BLIP[0], COLOR_RADAR_BLIP[1], COLOR_RADAR_BLIP[2], line_alpha)
            pygame.draw.line(
                overlay,
                line_color,
                (int(tank.x), int(tank.y)),
                (int(entity.x), int(entity.y)),
                1,
            )

        # Blit overlay to screen
        self.screen.blit(overlay, (0, 0))

    def set_perspective_tank(self, tank: "Tank | None") -> None:
        """Set which tank's perspective to render fog from.

        Args:
            tank: Tank to render perspective from, or None for no fog.

        """
        self.perspective_tank = tank
