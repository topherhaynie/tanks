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

            self._draw_tank(tank, alpha=255)

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
                self._draw_tank(tank, alpha=255)

    def render_observer(self, tanks: list["Tank"], observer_tanks: list["Tank"], hidden_alpha: float) -> None:
        """Render tanks for a global observer view with visibility cues.

        Args:
            tanks: List of tank entities to render.
            observer_tanks: Tanks whose vision determines visibility.
            hidden_alpha: Alpha to use for tanks hidden from opponents.

        """
        hidden_alpha_value = max(0, min(255, int(255 * hidden_alpha)))

        for tank in tanks:
            if not tank.active:
                continue

            visible_to_enemy = self._is_visible_to_enemy(tank, observer_tanks)
            alpha = 255 if visible_to_enemy else hidden_alpha_value
            self._draw_tank(tank, alpha=alpha)

    def _draw_tank(self, tank: "Tank", alpha: int) -> None:
        """Draw a tank body, turret, and HP bar.

        Args:
            tank: Tank entity to draw.
            alpha: Transparency level (0-255).

        """
        color = COLOR_TANK_FRIENDLY if tank.team == 0 else COLOR_TANK_ENEMY
        surface_size = int(tank.radius * 2 + 24)
        surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
        center = surface_size // 2

        body_color = (*color, alpha)
        pygame.draw.circle(surface, body_color, (center, center), tank.radius)

        angle_rad = math.radians(tank.angle)
        end_x = center + math.cos(angle_rad) * tank.radius
        end_y = center + math.sin(angle_rad) * tank.radius
        pygame.draw.line(surface, (255, 255, 255, alpha), (center, center), (end_x, end_y), 2)

        turret_angle_rad = math.radians(tank.turret_angle)
        turret_end_x = center + math.cos(turret_angle_rad) * (tank.radius + 8)
        turret_end_y = center + math.sin(turret_angle_rad) * (tank.radius + 8)
        pygame.draw.line(surface, (200, 200, 200, alpha), (center, center), (turret_end_x, turret_end_y), 4)

        self._draw_hp_bar(surface, tank, alpha)

        self._screen.blit(surface, (tank.x - center, tank.y - center))

    def _draw_hp_bar(self, surface: pygame.Surface, tank: "Tank", alpha: int) -> None:
        """Render health bar above tank.

        Args:
            surface: Surface to draw the HP bar on.
            tank: Tank entity to render HP bar for.
            alpha: Transparency level (0-255).

        """
        bar_width = tank.radius * 2
        bar_height = 4
        center = surface.get_width() // 2
        bar_x = center - bar_width / 2
        bar_y = center - tank.radius - 10

        pygame.draw.rect(surface, (200, 50, 50, alpha), (bar_x, bar_y, bar_width, bar_height))

        hp_ratio = tank.hp / tank.max_hp
        pygame.draw.rect(surface, (50, 200, 50, alpha), (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def _is_visible_to_enemy(self, tank: "Tank", observer_tanks: list["Tank"]) -> bool:
        has_enemy = False
        for observer in observer_tanks:
            if observer.team == tank.team:
                continue
            has_enemy = True
            if tank in observer.visible_entities:
                return True
        return not has_enemy
