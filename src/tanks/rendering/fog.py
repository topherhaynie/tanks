"""Fog-of-war rendering helpers."""

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pygame

from tanks.config.constants import (
    COLOR_FOG,
    FOG_GRADIENT_SCALE,
    FOG_TILE_SIZE,
    TILE_SIZE,
)

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
        self._fog_gradient_stamps: dict[tuple[int, int, int, int], pygame.Surface] = {}

    def render(self, game_map: "Map", tank: "Tank") -> None:
        """Render fog of war based on tank's terrain memory.

        Args:
            game_map: The game map.
            tank: Tank whose perspective to render from.

        """
        if not tank.fog_memory:
            return

        self.render_for_memory(game_map, tank.fog_memory, COLOR_FOG, opacity_scale=1.0)

    def render_for_memory(
        self,
        game_map: "Map",
        fog_memory: Any,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        opacity_scale: float,
    ) -> None:
        """Render fog of war for a fog memory with custom coloring.

        Args:
            game_map: The game map.
            fog_memory: Fog memory to render.
            color: Base fog color (RGB or RGBA).
            opacity_scale: Scalar applied to the base alpha.

        """
        context = FogContext(fog_memory)
        fog_color = _scale_fog_color(color, opacity_scale)
        gradient_stamp = self._get_fog_gradient_stamp(fog_color)

        map_width_px = game_map.width * TILE_SIZE
        map_height_px = game_map.height * TILE_SIZE
        fog_surface = pygame.Surface((map_width_px, map_height_px), pygame.SRCALPHA)

        # First pass: Draw solid fog tiles for unrevealed areas
        for x, y in context.iter_coords():
            if not context.is_revealed(x, y):
                fog_rect = pygame.Rect(
                    x * FOG_TILE_SIZE,
                    y * FOG_TILE_SIZE,
                    FOG_TILE_SIZE,
                    FOG_TILE_SIZE,
                )
                pygame.draw.rect(fog_surface, fog_color, fog_rect)

        # Second pass: Add smooth gradient at fog edges
        self._add_fog_gradients(fog_surface, context, gradient_stamp)

        self._screen.blit(fog_surface, (0, 0))

    def render_observer_fog(
        self,
        game_map: "Map",
        tanks: list["Tank"],
        fog_colors: tuple[tuple[int, int, int], ...],
        undiscovered_opacity: float = 0.4,
        team_tint_opacity: float = 0.35,
    ) -> None:
        """Render fog of war for observer mode with team coloring.

        Behavior:
        - Undiscovered areas (no tank has explored): Semi-transparent dark fog (reveals walls/background)
        - Discovered areas (tanks have explored): Normal view + visible team color tint
        - Multiple tanks discover same area: Tints layer naturally (soft color blending)
        - Fully revealed: Normal view with no fog

        Args:
            game_map: The game map.
            tanks: List of tanks with fog memories.
            fog_colors: Tuple of RGB colors for each tank's fog.
            undiscovered_opacity: Opacity for undiscovered areas (0-1), more transparent than normal.
            team_tint_opacity: Opacity for team color tints on discovered areas (0-1).

        """
        map_width_px = game_map.width * TILE_SIZE
        map_height_px = game_map.height * TILE_SIZE

        if not tanks or not tanks[0].fog_memory:
            return

        context = FogContext(tanks[0].fog_memory)

        # First pass: Semi-transparent dark fog for completely undiscovered areas
        undiscovered_fog_color = (
            COLOR_FOG[0],
            COLOR_FOG[1],
            COLOR_FOG[2],
            int(255 * undiscovered_opacity),
        )
        undiscovered_surface = pygame.Surface(
            (map_width_px, map_height_px),
            pygame.SRCALPHA,
        )

        # Draw dark fog only where NO tank has revealed
        for x, y in context.iter_coords():
            any_revealed = any(
                tank.fog_memory and tank.fog_memory.is_revealed(x, y)
                for tank in tanks
                if tank.fog_memory
            )

            if not any_revealed:
                fog_rect = pygame.Rect(
                    x * FOG_TILE_SIZE,
                    y * FOG_TILE_SIZE,
                    FOG_TILE_SIZE,
                    FOG_TILE_SIZE,
                )
                pygame.draw.rect(undiscovered_surface, undiscovered_fog_color, fog_rect)

        # Add gradients at edges of undiscovered fog
        undiscovered_gradient = self._get_fog_gradient_stamp(undiscovered_fog_color)
        self._add_fog_gradients_observer(
            undiscovered_surface, tanks, undiscovered_gradient
        )

        # Blit undiscovered fog with normal alpha blending (reveals background through transparency)
        self._screen.blit(undiscovered_surface, (0, 0))

        # Second pass: Colored tints for each tank's discovered areas with gradients
        for index, tank in enumerate(tanks):
            if not tank.fog_memory:
                continue

            color = fog_colors[index % len(fog_colors)]

            # Use the pure team color with moderate opacity for clear identification
            team_tint_color = (
                color[0],
                color[1],
                color[2],
                int(255 * team_tint_opacity),
            )

            team_surface = pygame.Surface(
                (map_width_px, map_height_px),
                pygame.SRCALPHA,
            )
            tank_context = FogContext(tank.fog_memory)

            # Draw color tint only for this tank's DISCOVERED areas
            for x, y in tank_context.iter_coords():
                if tank_context.is_revealed(x, y):
                    fog_rect = pygame.Rect(
                        x * FOG_TILE_SIZE,
                        y * FOG_TILE_SIZE,
                        FOG_TILE_SIZE,
                        FOG_TILE_SIZE,
                    )
                    pygame.draw.rect(team_surface, team_tint_color, fog_rect)

            # Add gradients to smooth out blocky edges of team coloring
            team_gradient = self._get_fog_gradient_stamp(team_tint_color)
            self._add_team_fog_gradients(team_surface, tank, team_gradient)

            # Blit with normal alpha blending so tints layer naturally
            self._screen.blit(team_surface, (0, 0))

    def _add_fog_gradients_observer(
        self,
        fog_surface: pygame.Surface,
        tanks: list["Tank"],
        gradient_stamp: pygame.Surface,
    ) -> None:
        """Add gradients at fog edges for observer base fog.

        Args:
            fog_surface: Surface to draw gradients on.
            tanks: List of tanks to check for revealed areas.
            gradient_stamp: Pre-rendered gradient stamp to blit.

        """
        if not tanks or not tanks[0].fog_memory:
            return

        context = FogContext(tanks[0].fog_memory)
        stamp_radius = gradient_stamp.get_width() // 2

        for x, y in context.iter_coords():
            # Check if any tank has revealed this tile
            any_revealed = any(
                tank.fog_memory and tank.fog_memory.is_revealed(x, y)
                for tank in tanks
                if tank.fog_memory
            )

            # Check if any neighbor is unrevealed by all tanks
            has_unrevealed_neighbor = False
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    neighbor_revealed = any(
                        tank.fog_memory and tank.fog_memory.is_revealed(x + dx, y + dy)
                        for tank in tanks
                        if tank.fog_memory
                    )
                    if not neighbor_revealed:
                        has_unrevealed_neighbor = True
                        break
                if has_unrevealed_neighbor:
                    break

            if any_revealed and has_unrevealed_neighbor:
                center_x = int((x + 0.5) * FOG_TILE_SIZE)
                center_y = int((y + 0.5) * FOG_TILE_SIZE)

                fog_surface.blit(
                    gradient_stamp,
                    (center_x - stamp_radius, center_y - stamp_radius),
                    special_flags=pygame.BLEND_RGBA_MAX,
                )

    def _add_team_fog_gradients(
        self,
        fog_surface: pygame.Surface,
        tank: "Tank",
        gradient_stamp: pygame.Surface,
    ) -> None:
        """Add gradients at edges of team fog to smooth blocky appearance.

        Args:
            fog_surface: Surface to draw gradients on.
            tank: Tank whose fog memory to check.
            gradient_stamp: Pre-rendered gradient stamp to blit.

        """
        if not tank.fog_memory:
            return

        context = FogContext(tank.fog_memory)
        stamp_radius = gradient_stamp.get_width() // 2

        for x, y in context.iter_coords():
            if context.is_revealed(x, y) and context.has_unrevealed_neighbor(x, y):
                center_x = int((x + 0.5) * FOG_TILE_SIZE)
                center_y = int((y + 0.5) * FOG_TILE_SIZE)

                fog_surface.blit(
                    gradient_stamp,
                    (center_x - stamp_radius, center_y - stamp_radius),
                    special_flags=pygame.BLEND_RGBA_MAX,
                )

    def _get_fog_gradient_stamp(
        self,
        fog_color: tuple[int, int, int, int],
    ) -> pygame.Surface:
        """Get a cached fog gradient stamp for a given color.

        Returns:
            Gradient stamp surface.

        """
        if fog_color in self._fog_gradient_stamps:
            return self._fog_gradient_stamps[fog_color]

        stamp_radius = int(FOG_TILE_SIZE * FOG_GRADIENT_SCALE)
        stamp_size = stamp_radius * 2
        stamp = pygame.Surface((stamp_size, stamp_size), pygame.SRCALPHA)

        gradient_steps = 16
        base_alpha = fog_color[3]
        for i in range(gradient_steps):
            progress = i / gradient_steps
            radius = int(stamp_radius * (1.0 - progress * 0.6))

            alpha = int(base_alpha * (progress**2))
            color = (fog_color[0], fog_color[1], fog_color[2], alpha)

            pygame.draw.circle(stamp, color, (stamp_radius, stamp_radius), radius)

        self._fog_gradient_stamps[fog_color] = stamp
        return stamp

    def _add_fog_gradients(
        self,
        fog_surface: pygame.Surface,
        context: "FogContext",
        gradient_stamp: pygame.Surface,
    ) -> None:
        """Add smooth gradients at fog edges for revealed tiles.

        Args:
            fog_surface: Surface to draw gradients on.
            context: Fog access helper for tile visibility.
            gradient_stamp: Pre-rendered gradient stamp to blit.

        """
        stamp_radius = gradient_stamp.get_width() // 2

        for x, y in context.iter_coords():
            if context.is_revealed(x, y) and context.has_unrevealed_neighbor(x, y):
                center_x = int((x + 0.5) * FOG_TILE_SIZE)
                center_y = int((y + 0.5) * FOG_TILE_SIZE)

                fog_surface.blit(
                    gradient_stamp,
                    (center_x - stamp_radius, center_y - stamp_radius),
                    special_flags=pygame.BLEND_RGBA_MAX,
                )


# Color tuple length constants
RGB_TUPLE_LENGTH = 3


def _scale_fog_color(
    color: tuple[int, int, int] | tuple[int, int, int, int],
    opacity_scale: float,
) -> tuple[int, int, int, int]:
    if len(color) == RGB_TUPLE_LENGTH:
        red, green, blue = color
        alpha = 255
    else:
        red, green, blue, alpha = color

    scaled_alpha = max(0, min(255, int(alpha * opacity_scale)))
    return red, green, blue, scaled_alpha


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
