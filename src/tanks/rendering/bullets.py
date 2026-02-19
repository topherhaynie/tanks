"""Bullet rendering helpers."""

from typing import TYPE_CHECKING

import pygame

from tanks.config.constants import COLOR_BULLET

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class BulletRenderer:
    """Draw bullets with optional visibility filtering."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize bullet renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render_all(self, bullets: list) -> None:
        """Render all bullets.

        Args:
            bullets: List of bullet entities to render.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            pygame.draw.circle(
                self._screen,
                COLOR_BULLET,
                (int(bullet.x), int(bullet.y)),
                bullet.radius,
            )

    def render_visible(self, bullets: list, perspective_tank: "Tank") -> None:
        """Render bullets visible to the perspective tank.

        Args:
            bullets: List of bullet entities to render.
            perspective_tank: Tank whose perspective determines visibility.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            if bullet in perspective_tank.visible_entities:
                pygame.draw.circle(
                    self._screen,
                    COLOR_BULLET,
                    (int(bullet.x), int(bullet.y)),
                    bullet.radius,
                )
