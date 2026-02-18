"""Debug visualization utilities."""

import pygame


class DebugRenderer:
    """Renders debug overlays and information."""

    @staticmethod
    def draw_vision_cone(screen, tank, radius, color):
        """Draw vision cone overlay."""
        pygame.draw.circle(screen, color, (int(tank.x), int(tank.y)), radius, 1)

    @staticmethod
    def draw_radar_overlay(screen, tank, radius, color):
        """Draw radar range overlay."""
        pygame.draw.circle(screen, color, (int(tank.x), int(tank.y)), radius, 1)

    @staticmethod
    def draw_text(screen, font, text, x, y, color=(255, 255, 255)):
        """Draw debug text."""
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, (x, y))
