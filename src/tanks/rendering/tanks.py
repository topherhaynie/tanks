"""Tank rendering helpers."""

import math
from typing import TYPE_CHECKING

import pygame

from tanks.config.constants import COLOR_TANK_ENEMY, COLOR_TANK_FRIENDLY

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class TankRenderer:
    """Draw tanks and related HUD elements."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize tank renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render_all(self, tanks: list["Tank"]) -> None:
        """Render all tanks.

        Args:
            tanks: List of tank entities to render.

        """
        for tank in tanks:
            if not tank.active:
                continue

            self._draw_tank(tank)

    def render_visible(self, tanks: list["Tank"], perspective_tank: "Tank") -> None:
        """Render tanks visible to the perspective tank.

        Args:
            tanks: List of tank entities to render.
            perspective_tank: Tank whose perspective determines visibility.

        """
        for tank in tanks:
            if not tank.active:
                continue

            if tank == perspective_tank or tank in perspective_tank.visible_entities:
                self._draw_tank(tank)

    def _draw_tank(self, tank: "Tank") -> None:
        """Draw a tank body, turret, and HP bar.

        Args:
            tank: Tank entity to draw.

        """
        color = COLOR_TANK_FRIENDLY if tank.team == 0 else COLOR_TANK_ENEMY

        # Draw body (circle)
        pygame.draw.circle(self._screen, color, (int(tank.x), int(tank.y)), tank.radius)

        # Draw direction indicator on body
        angle_rad = math.radians(tank.angle)
        end_x = tank.x + math.cos(angle_rad) * tank.radius
        end_y = tank.y + math.sin(angle_rad) * tank.radius
        pygame.draw.line(self._screen, (255, 255, 255), (tank.x, tank.y), (end_x, end_y), 2)

        # Draw turret
        turret_angle_rad = math.radians(tank.turret_angle)
        turret_end_x = tank.x + math.cos(turret_angle_rad) * (tank.radius + 8)
        turret_end_y = tank.y + math.sin(turret_angle_rad) * (tank.radius + 8)
        pygame.draw.line(self._screen, (200, 200, 200), (tank.x, tank.y), (turret_end_x, turret_end_y), 4)

        self._draw_hp_bar(tank)

    def _draw_hp_bar(self, tank: "Tank") -> None:
        """Render health bar above tank.

        Args:
            tank: Tank entity to render HP bar for.

        """
        bar_width = tank.radius * 2
        bar_height = 4
        bar_x = tank.x - bar_width / 2
        bar_y = tank.y - tank.radius - 10

        # Red background bar
        pygame.draw.rect(self._screen, (200, 50, 50), (bar_x, bar_y, bar_width, bar_height))

        # Green foreground bar
        hp_ratio = tank.hp / tank.max_hp
        pygame.draw.rect(self._screen, (50, 200, 50), (bar_x, bar_y, bar_width * hp_ratio, bar_height))
