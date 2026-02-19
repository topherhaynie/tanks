"""Visual effects rendering helpers."""

import pygame

from tanks.effects.visual import VisualEffect


class EffectsRenderer:
    """Render visual effects."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize effects renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render(self, effects: list[VisualEffect]) -> None:
        """Render visual effects.

        Args:
            effects: List of visual effects to render.

        """
        for effect in effects:
            if not effect.active:
                continue

            effect.render(self._screen)
