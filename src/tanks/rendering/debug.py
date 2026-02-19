"""Debug visualization utilities."""

from typing import Any

import pygame

from tanks.config.constants import COLOR_DEBUG_HITBOX


class DebugRenderer:
    """Renders debug overlays and information."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize debug renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render_hitboxes(self, game_state: Any) -> None:
        """Render debug hitboxes.

        Args:
            game_state: Current game state.

        """
        for tank in game_state.tanks:
            if tank.active:
                pygame.draw.circle(self._screen, COLOR_DEBUG_HITBOX, (int(tank.x), int(tank.y)), tank.radius, 1)

        for bullet in game_state.bullets:
            if bullet.active:
                pygame.draw.circle(self._screen, COLOR_DEBUG_HITBOX, (int(bullet.x), int(bullet.y)), bullet.radius, 1)

    @staticmethod
    def draw_vision_cone(screen: pygame.Surface, tank: Any, radius: int, color: tuple[int, int, int]) -> None:
        """Draw vision cone overlay."""
        pygame.draw.circle(screen, color, (int(tank.x), int(tank.y)), radius, 1)

    @staticmethod
    def draw_radar_overlay(screen: pygame.Surface, tank: Any, radius: int, color: tuple[int, int, int]) -> None:
        """Draw radar range overlay."""
        pygame.draw.circle(screen, color, (int(tank.x), int(tank.y)), radius, 1)

    @staticmethod
    def draw_text(
        screen: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        """Draw debug text."""
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, (x, y))
