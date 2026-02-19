"""Map rendering helpers."""

from typing import TYPE_CHECKING

import pygame

from tanks.config.constants import (
    COLOR_WALL,
    TILE_SIZE,
    TILE_WALL_DIAGONAL_NE,
    TILE_WALL_DIAGONAL_NW,
    TILE_WALL_HORIZONTAL,
    TILE_WALL_SOLID,
    TILE_WALL_VERTICAL,
)

if TYPE_CHECKING:
    from tanks.maps.map import Map


class MapRenderer:
    """Draw the tile-based map."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize map renderer.

        Args:
            screen: Pygame surface to render to.

        """
        self._screen = screen

    def render(self, game_map: "Map") -> None:
        """Render the tile-based map.

        Args:
            game_map: Map object to render.

        """
        if not game_map:
            return

        for y in range(game_map.height):
            for x in range(game_map.width):
                tile_type = game_map.get_tile(x, y)
                if tile_type > 0:
                    self._render_tile(x, y, tile_type)

    def _render_tile(self, tx: int, ty: int, tile_type: int) -> None:
        """Render a single tile.

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.
            tile_type: Type of tile to render.

        """
        x = tx * TILE_SIZE
        y = ty * TILE_SIZE

        if tile_type == TILE_WALL_HORIZONTAL:
            pygame.draw.line(self._screen, COLOR_WALL, (x, y + TILE_SIZE // 2), (x + TILE_SIZE, y + TILE_SIZE // 2), 3)
        elif tile_type == TILE_WALL_VERTICAL:
            pygame.draw.line(self._screen, COLOR_WALL, (x + TILE_SIZE // 2, y), (x + TILE_SIZE // 2, y + TILE_SIZE), 3)
        elif tile_type == TILE_WALL_DIAGONAL_NE:
            pygame.draw.line(self._screen, COLOR_WALL, (x, y + TILE_SIZE), (x + TILE_SIZE, y), 3)
        elif tile_type == TILE_WALL_DIAGONAL_NW:
            pygame.draw.line(self._screen, COLOR_WALL, (x, y), (x + TILE_SIZE, y + TILE_SIZE), 3)
        elif tile_type == TILE_WALL_SOLID:
            pygame.draw.rect(self._screen, COLOR_WALL, (x, y, TILE_SIZE, TILE_SIZE))
