"""Radar and vision overlay rendering helpers."""

import math
from typing import TYPE_CHECKING

import pygame

from tanks.config.constants import (
    COLOR_RADAR_BLIP_MINE,
    COLOR_RADAR_BLIP_TANK,
    COLOR_RADAR_JAMMING,
    COLOR_RADAR_OVERLAY,
    COLOR_RADAR_SWEEP,
    COLOR_RADAR_SWEEP_BAR,
    COLOR_VISION_OVERLAY,
    RADAR_BLIP_FADE_TIME,
    RADAR_JAMMING_RADIUS,
    RADAR_VISUAL_RADIUS,
    VISION_RADIUS,
)

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class RadarRenderer:
    """Draw radar sweep, blips, and debug overlays."""

    def __init__(self, screen: pygame.Surface, small_font: pygame.font.Font) -> None:
        """Initialize radar renderer.

        Args:
            screen: Pygame surface to render to.
            small_font: Font for radar-related text.

        """
        self._screen = screen
        self._small_font = small_font

    def render_vision_debug(self, tank: "Tank") -> None:
        """Render debug visualization for vision and radar ranges.

        Args:
            tank: Tank to visualize vision for.

        """
        if not tank.active:
            return

        # Create a surface with per-pixel alpha for overlays
        overlay = pygame.Surface((self._screen.get_width(), self._screen.get_height()), pygame.SRCALPHA)

        # Draw vision circle
        pygame.draw.circle(overlay, COLOR_VISION_OVERLAY, (int(tank.x), int(tank.y)), int(VISION_RADIUS))

        # Draw radar circle
        pygame.draw.circle(
            overlay,
            COLOR_RADAR_OVERLAY,
            (int(tank.x), int(tank.y)),
            int(RADAR_VISUAL_RADIUS),
            2,
        )

        # Draw radar sweep line
        sweep_rad = math.radians(tank.radar_sweep_angle)
        sweep_end_x = tank.x + math.cos(sweep_rad) * RADAR_VISUAL_RADIUS
        sweep_end_y = tank.y + math.sin(sweep_rad) * RADAR_VISUAL_RADIUS
        pygame.draw.line(overlay, COLOR_RADAR_SWEEP, (tank.x, tank.y), (sweep_end_x, sweep_end_y), 2)

        # Blit overlay to screen
        self._screen.blit(overlay, (0, 0))

    def render_blips(self, tank: "Tank", current_time: float) -> None:
        """Render radar sweep bar and fading blips for detected entities.

        Args:
            tank: Tank whose radar to render.
            current_time: Timestamp for consistent radar timing this frame.

        """
        if not tank.active or not hasattr(tank, "radar_sweep_angle"):
            return

        # Create overlay surface
        overlay = pygame.Surface((self._screen.get_width(), self._screen.get_height()), pygame.SRCALPHA)

        # Draw rotating green sweep line (counter-clockwise)
        sweep_angle_rad = math.radians(tank.radar_sweep_angle)
        sweep_end_x = tank.x + math.cos(sweep_angle_rad) * RADAR_VISUAL_RADIUS
        sweep_end_y = tank.y + math.sin(sweep_angle_rad) * RADAR_VISUAL_RADIUS
        pygame.draw.line(overlay, COLOR_RADAR_SWEEP_BAR, (tank.x, tank.y), (sweep_end_x, sweep_end_y), 2)

        # Draw fading blips for detected entities
        if hasattr(tank, "radar_blips"):
            for entity, blip_time, _angle, snap_x, snap_y, entity_type in tank.radar_blips:
                if not entity.active:
                    continue

                # Calculate fade based on time
                age = current_time - blip_time
                if age >= RADAR_BLIP_FADE_TIME:
                    continue

                fade_ratio = 1.0 - (age / RADAR_BLIP_FADE_TIME)

                # Determine color based on entity type (from snapshot)
                base_color = COLOR_RADAR_BLIP_MINE if entity_type == "Mine" else COLOR_RADAR_BLIP_TANK

                # Apply fade to alpha
                blip_alpha = int(base_color[3] * fade_ratio)
                blip_color = (base_color[0], base_color[1], base_color[2], blip_alpha)

                # Draw pulsing blip
                pulse = 1.0 + 0.2 * math.sin(current_time * 10)
                blip_size = int(10 * fade_ratio * pulse)

                # Draw outer ring at snapshot position
                pygame.draw.circle(
                    overlay,
                    blip_color,
                    (int(snap_x), int(snap_y)),
                    blip_size + 3,
                    2,
                )

                # Draw inner filled circle
                inner_alpha = int(blip_alpha * 0.6)
                inner_color = (base_color[0], base_color[1], base_color[2], inner_alpha)
                pygame.draw.circle(
                    overlay,
                    inner_color,
                    (int(snap_x), int(snap_y)),
                    blip_size,
                )

        # Blit overlay to screen
        self._screen.blit(overlay, (0, 0))

    def render_jamming_effects(self, tanks: list["Tank"]) -> None:
        """Render radar jamming visual effects.

        Args:
            tanks: List of all tanks to check for active jamming.

        """
        overlay = pygame.Surface((self._screen.get_width(), self._screen.get_height()), pygame.SRCALPHA)

        for tank in tanks:
            if not tank.active:
                continue

            # Check if tank has jamming active
            if hasattr(tank, "jamming_active") and tank.jamming_active:
                # Draw pulsing jamming effect circle
                pulse_scale = 1.0 + 0.2 * math.sin(tank.radar_sweep_angle * math.pi / 180 * 6)
                jamming_radius = int(RADAR_JAMMING_RADIUS * pulse_scale)

                # Draw multiple concentric circles for wave effect
                for i in range(3):
                    radius_offset = i * 30
                    alpha = max(0, int(COLOR_RADAR_JAMMING[3] * (1.0 - i * 0.3)))
                    color = (COLOR_RADAR_JAMMING[0], COLOR_RADAR_JAMMING[1], COLOR_RADAR_JAMMING[2], alpha)
                    pygame.draw.circle(
                        overlay,
                        color,
                        (int(tank.x), int(tank.y)),
                        jamming_radius - radius_offset,
                        2,
                    )

                # Draw "JAMMING" text above tank
                jam_text = "JAMMING"
                text_surface = self._small_font.render(jam_text, True, (255, 100, 100))
                text_bg = pygame.Surface((text_surface.get_width() + 4, text_surface.get_height() + 2), pygame.SRCALPHA)
                text_bg.fill((0, 0, 0, 180))

                text_x = int(tank.x) - text_surface.get_width() // 2
                text_y = int(tank.y) - tank.radius - 30

                overlay.blit(text_bg, (text_x - 2, text_y - 1))
                overlay.blit(text_surface, (text_x, text_y))

        self._screen.blit(overlay, (0, 0))
