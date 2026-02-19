"""Map rendering helpers."""

from typing import TYPE_CHECKING, Any

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

    def render(self, game_map: "Map", camera: Any = None) -> None:
        """Render the tile-based map.

        Args:
            game_map: Map object to render.
            camera: Optional camera for viewport culling and transforms.

        """
        if not game_map:
            return

        for y in range(game_map.height):
            for x in range(game_map.width):
                tile_type = game_map.get_tile(x, y)
                if tile_type > 0:
                    self._render_tile(x, y, tile_type, camera)

    def _render_tile(
        self,
        tx: int,
        ty: int,
        tile_type: int,
        camera: Any = None,
    ) -> None:
        """Render a single tile.

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.
            tile_type: Type of tile to render.
            camera: Optional camera for viewport transforms.

        """
        # World coordinates
        world_x = tx * TILE_SIZE
        world_y = ty * TILE_SIZE

        # Skip if not visible (with margin for lines)
        if camera and not camera.is_visible(world_x, world_y, margin=TILE_SIZE):
            return

        # Convert to screen coordinates
        if camera:
            screen_x, screen_y = camera.world_to_screen(world_x, world_y)
            tile_size = TILE_SIZE * camera.zoom
        else:
            screen_x, screen_y = world_x, world_y
            tile_size = TILE_SIZE

        if tile_type == TILE_WALL_HORIZONTAL:
            pygame.draw.line(
                self._screen,
                COLOR_WALL,
                (screen_x, screen_y + tile_size // 2),
                (screen_x + tile_size, screen_y + tile_size // 2),
                max(1, int(3 * camera.zoom)) if camera else 3,
            )
        elif tile_type == TILE_WALL_VERTICAL:
            pygame.draw.line(
                self._screen,
                COLOR_WALL,
                (screen_x + tile_size // 2, screen_y),
                (screen_x + tile_size // 2, screen_y + tile_size),
                max(1, int(3 * camera.zoom)) if camera else 3,
            )
        elif tile_type == TILE_WALL_DIAGONAL_NE:
            pygame.draw.line(
                self._screen,
                COLOR_WALL,
                (screen_x, screen_y + tile_size),
                (screen_x + tile_size, screen_y),
                max(1, int(3 * camera.zoom)) if camera else 3,
            )
        elif tile_type == TILE_WALL_DIAGONAL_NW:
            pygame.draw.line(
                self._screen,
                COLOR_WALL,
                (screen_x, screen_y),
                (screen_x + tile_size, screen_y + tile_size),
                max(1, int(3 * camera.zoom)) if camera else 3,
            )
        elif tile_type == TILE_WALL_SOLID:
            pygame.draw.rect(
                self._screen,
                COLOR_WALL,
                (screen_x, screen_y, tile_size, tile_size),
            )
