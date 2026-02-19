"""HUD rendering helpers."""

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class HudRenderer:
    """Draw HUD elements like FPS and status text."""

    def __init__(self, screen: pygame.Surface, small_font: pygame.font.Font) -> None:
        """Initialize HUD renderer.

        Args:
            screen: Pygame surface to render to.
            small_font: Font for HUD text.

        """
        self._screen = screen
        self._small_font = small_font

    def render_fps(self, fps: float) -> None:
        """Render FPS counter.

        Args:
            fps: Current frames per second.

        """
        fps_text = self._small_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
        self._screen.blit(fps_text, (10, 10))

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

        text_surface = self._small_font.render(status_text, True, color)
        self._screen.blit(text_surface, (10, y_offset))
