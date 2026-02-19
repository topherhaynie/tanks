"""Frame orchestration helpers."""

import pygame

from tanks.config.constants import COLOR_BACKGROUND


class FrameRenderer:
    """Handle per-frame begin/end rendering work."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize frame renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def begin(self) -> None:
        """Prepare the screen for a new frame."""
        self._screen.fill(COLOR_BACKGROUND)

    def end(self) -> None:
        """Present the rendered frame."""
        pygame.display.flip()
