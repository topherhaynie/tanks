"""Fog-of-war rendering helpers."""

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pygame

from tanks.config.constants import COLOR_FOG, FOG_GRADIENT_SCALE, FOG_TILE_SIZE, TILE_SIZE

if TYPE_CHECKING:
    from tanks.entities.tank import Tank
    from tanks.maps.map import Map


class FogRenderer:
    """Render fog of war with smooth gradients."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize fog renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen
        self._fog_gradient_stamp = self._create_fog_gradient_stamp()

    def render(self, game_map: "Map", tank: "Tank") -> None:
        """Render fog of war based on tank's terrain memory.

        Args:
            game_map: The game map.
            tank: Tank whose perspective to render from.

        """
        if not tank.fog_memory:
            return

        context = FogContext(tank.fog_memory)

        map_width_px = game_map.width * TILE_SIZE
        map_height_px = game_map.height * TILE_SIZE
        fog_surface = pygame.Surface((map_width_px, map_height_px), pygame.SRCALPHA)

        # First pass: Draw solid fog tiles for unrevealed areas
        for x, y in context.iter_coords():
            if not context.is_revealed(x, y):
                fog_rect = pygame.Rect(x * FOG_TILE_SIZE, y * FOG_TILE_SIZE, FOG_TILE_SIZE, FOG_TILE_SIZE)
                pygame.draw.rect(fog_surface, COLOR_FOG, fog_rect)

        # Second pass: Add smooth gradient at fog edges
        self._add_fog_gradients(fog_surface, context)

        self._screen.blit(fog_surface, (0, 0))

    def _create_fog_gradient_stamp(self) -> pygame.Surface:
        """Pre-render a fog gradient stamp for performance.

        Returns:
            Gradient stamp surface.

        """
        stamp_radius = int(FOG_TILE_SIZE * FOG_GRADIENT_SCALE)
        stamp_size = stamp_radius * 2
        stamp = pygame.Surface((stamp_size, stamp_size), pygame.SRCALPHA)

        gradient_steps = 16
        for i in range(gradient_steps):
            progress = i / gradient_steps
            radius = int(stamp_radius * (1.0 - progress * 0.6))

            alpha = int(COLOR_FOG[3] * (progress**2))
            color = (COLOR_FOG[0], COLOR_FOG[1], COLOR_FOG[2], alpha)

            pygame.draw.circle(stamp, color, (stamp_radius, stamp_radius), radius)

        return stamp

    def _add_fog_gradients(self, fog_surface: pygame.Surface, context: "FogContext") -> None:
        """Add smooth gradients at fog edges for revealed tiles.

        Args:
            fog_surface: Surface to draw gradients on.
            context: Fog access helper for tile visibility.

        """
        stamp_radius = self._fog_gradient_stamp.get_width() // 2

        for x, y in context.iter_coords():
            if context.is_revealed(x, y) and context.has_unrevealed_neighbor(x, y):
                center_x = int((x + 0.5) * FOG_TILE_SIZE)
                center_y = int((y + 0.5) * FOG_TILE_SIZE)

                fog_surface.blit(
                    self._fog_gradient_stamp,
                    (center_x - stamp_radius, center_y - stamp_radius),
                    special_flags=pygame.BLEND_RGBA_MAX,
                )


class FogContext:
    """Helper for accessing fog memory state."""

    def __init__(self, memory: Any) -> None:
        """Initialize fog context.

        Args:
            memory: Fog memory backing store.

        """
        self._memory = memory

    @property
    def width(self) -> int:
        """Return fog width in tiles."""
        return self._memory.fog_width

    @property
    def height(self) -> int:
        """Return fog height in tiles."""
        return self._memory.fog_height

    def iter_coords(self) -> Iterator[tuple[int, int]]:
        """Iterate over fog tile coordinates.

        Returns:
            Iterator of (x, y) fog coordinates.

        """
        for y in range(self.height):
            for x in range(self.width):
                yield x, y

    def is_revealed(self, x: int, y: int) -> bool:
        """Check if a fog tile is revealed.

        Args:
            x: Fog tile X coordinate.
            y: Fog tile Y coordinate.

        Returns:
            True if revealed.

        """
        return self._memory.is_revealed(x, y)

    def has_unrevealed_neighbor(self, x: int, y: int) -> bool:
        """Check if a tile has any unrevealed neighbors.

        Args:
            x: Fog tile X coordinate.
            y: Fog tile Y coordinate.

        Returns:
            True if any neighbor is unrevealed.

        """
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                if not self._memory.is_revealed(x + dx, y + dy):
                    return True
        return False
