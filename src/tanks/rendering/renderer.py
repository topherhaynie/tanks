"""Main renderer coordinating all drawing."""

import math
from typing import TYPE_CHECKING, Any

import pygame

if TYPE_CHECKING:
    from tanks.entities.tank import Tank
    from tanks.maps.map import Map

from tanks.config.constants import (
    COLOR_BACKGROUND,
    COLOR_BULLET,
    COLOR_DEBUG_HITBOX,
    COLOR_TANK_ENEMY,
    COLOR_TANK_FRIENDLY,
    COLOR_WALL,
    TILE_SIZE,
    TILE_WALL_DIAGONAL_NE,
    TILE_WALL_DIAGONAL_NW,
    TILE_WALL_HORIZONTAL,
    TILE_WALL_SOLID,
    TILE_WALL_VERTICAL,
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

        # Initialize font for debug text
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

    def render_frame(self, game_state: Any) -> None:
        """Render a complete frame.

        Args:
            game_state: Current game state to render.

        """
        # Clear screen
        self.screen.fill(COLOR_BACKGROUND)

        # Layer 1: Map
        self.render_map(game_state.game_map)

        # Layer 2: Entities
        self.render_bullets(game_state.bullets)
        self.render_tanks(game_state.tanks)

        # Layer 3: Debug overlays
        if self.settings.show_hitboxes:
            self.render_hitboxes(game_state)

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

    def render_bullets(self, bullets: list) -> None:
        """Render all bullets.

        Args:
            bullets: List of bullet entities to render.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            pygame.draw.circle(self.screen, COLOR_BULLET, (int(bullet.x), int(bullet.y)), bullet.radius)

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
