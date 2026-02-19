"""Missile and mine rendering helpers."""

from typing import TYPE_CHECKING, Any

import pygame

from tanks.config.constants import COLOR_MINE, COLOR_MISSILE

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class ProjectileRenderer:
    """Draw missiles and mines with optional visibility filtering."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize projectile renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render_all_missiles(self, missiles: list, camera: Any = None) -> None:
        """Render all missiles.

        Args:
            missiles: List of missile entities to render.
            camera: Optional camera for viewport transforms.

        """
        for missile in missiles:
            if not missile.active:
                continue

            # Skip if not visible in viewport
            if camera and not camera.is_visible(missile.x, missile.y, margin=50):
                continue

            # Convert to screen coordinates
            if camera:
                screen_x, screen_y = camera.world_to_screen(missile.x, missile.y)
                radius = max(1, int(missile.radius * camera.zoom))
            else:
                screen_x, screen_y = missile.x, missile.y
                radius = missile.radius

            pygame.draw.circle(
                self._screen,
                COLOR_MISSILE,
                (int(screen_x), int(screen_y)),
                radius,
            )

    def render_all_mines(self, mines: list, camera: Any = None) -> None:
        """Render all mines.

        Args:
            mines: List of mine entities to render.
            camera: Optional camera for viewport transforms.

        """
        for mine in mines:
            if not mine.active:
                continue

            # Skip if not visible in viewport
            if camera and not camera.is_visible(mine.x, mine.y, margin=50):
                continue

            # Convert to screen coordinates
            if camera:
                screen_x, screen_y = camera.world_to_screen(mine.x, mine.y)
                radius = max(1, int(mine.radius * camera.zoom))
            else:
                screen_x, screen_y = mine.x, mine.y
                radius = mine.radius

            pygame.draw.circle(
                self._screen,
                COLOR_MINE,
                (int(screen_x), int(screen_y)),
                radius,
            )

    def render_visible_missiles(
        self,
        missiles: list,
        perspective_tank: "Tank",
        camera: Any = None,
    ) -> None:
        """Render missiles visible to the perspective tank.

        Args:
            missiles: List of missile entities to render.
            perspective_tank: Tank whose perspective determines visibility.
            camera: Optional camera for viewport transforms.

        """
        for missile in missiles:
            if not missile.active:
                continue

            # Skip if not visible in viewport
            if camera and not camera.is_visible(missile.x, missile.y, margin=50):
                continue

            if missile in perspective_tank.visible_entities:
                # Convert to screen coordinates
                if camera:
                    screen_x, screen_y = camera.world_to_screen(missile.x, missile.y)
                    radius = max(1, int(missile.radius * camera.zoom))
                else:
                    screen_x, screen_y = missile.x, missile.y
                    radius = missile.radius

                pygame.draw.circle(
                    self._screen,
                    COLOR_MISSILE,
                    (int(screen_x), int(screen_y)),
                    radius,
                )

    def render_visible_mines(
        self,
        mines: list,
        perspective_tank: "Tank",
        camera: Any = None,
    ) -> None:
        """Render mines visible to the perspective tank.

        Args:
            mines: List of mine entities to render.
            perspective_tank: Tank whose perspective determines visibility.
            camera: Optional camera for viewport transforms.

        """
        for mine in mines:
            if not mine.active:
                continue

            # Skip if not visible in viewport
            if camera and not camera.is_visible(mine.x, mine.y, margin=50):
                continue

            if mine in perspective_tank.visible_entities:
                # Convert to screen coordinates
                if camera:
                    screen_x, screen_y = camera.world_to_screen(mine.x, mine.y)
                    radius = max(1, int(mine.radius * camera.zoom))
                else:
                    screen_x, screen_y = mine.x, mine.y
                    radius = mine.radius

                pygame.draw.circle(
                    self._screen,
                    COLOR_MINE,
                    (int(screen_x), int(screen_y)),
                    radius,
                )
