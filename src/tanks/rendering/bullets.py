"""Bullet rendering helpers."""

from typing import TYPE_CHECKING, Any

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

    def render_all(self, bullets: list, camera: Any = None) -> None:
        """Render all bullets.

        Args:
            bullets: List of bullet entities to render.
            camera: Optional camera for viewport transforms.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            # Skip if not visible in viewport
            if camera and not camera.is_visible(bullet.x, bullet.y, margin=50):
                continue

            # Convert to screen coordinates
            if camera:
                screen_x, screen_y = camera.world_to_screen(bullet.x, bullet.y)
                radius = max(1, int(bullet.radius * camera.zoom))
            else:
                screen_x, screen_y = bullet.x, bullet.y
                radius = bullet.radius

            pygame.draw.circle(
                self._screen,
                COLOR_BULLET,
                (int(screen_x), int(screen_y)),
                radius,
            )

    def render_visible(
        self,
        bullets: list,
        perspective_tank: "Tank",
        camera: Any = None,
    ) -> None:
        """Render bullets visible to the perspective tank.

        Args:
            bullets: List of bullet entities to render.
            perspective_tank: Tank whose perspective determines visibility.
            camera: Optional camera for viewport transforms.

        """
        for bullet in bullets:
            if not bullet.active:
                continue

            # Skip if not visible in viewport
            if camera and not camera.is_visible(bullet.x, bullet.y, margin=50):
                continue

            if bullet in perspective_tank.visible_entities:
                # Convert to screen coordinates
                if camera:
                    screen_x, screen_y = camera.world_to_screen(bullet.x, bullet.y)
                    radius = max(1, int(bullet.radius * camera.zoom))
                else:
                    screen_x, screen_y = bullet.x, bullet.y
                    radius = bullet.radius

                pygame.draw.circle(
                    self._screen,
                    COLOR_BULLET,
                    (int(screen_x), int(screen_y)),
                    radius,
                )
