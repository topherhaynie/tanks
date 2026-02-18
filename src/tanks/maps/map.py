"""Map representation using tile grid."""

from tanks.config.constants import TILE_EMPTY, TILE_SIZE


class Map:
    """Tile-based game map."""

    def __init__(self, width: int, height: int, tiles: list[list[int]] | None = None) -> None:
        """Create a map.

        Args:
            width: Width in tiles.
            height: Height in tiles.
            tiles: 2D list of tile types, or None for empty map.

        """
        self.width = width
        self.height = height

        if tiles is None:
            # Create empty map
            self.tiles = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]
        else:
            self.tiles = tiles

        self.spawn_points: list[dict[str, int | float]] = []

    def get_tile(self, tx: int, ty: int) -> int:
        """Get tile type at grid coordinates.

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.

        Returns:
            Tile type at the specified coordinates.

        """
        if 0 <= ty < self.height and 0 <= tx < self.width:
            return self.tiles[ty][tx]
        return TILE_EMPTY

    def set_tile(self, tx: int, ty: int, tile_type: int) -> None:
        """Set tile type at grid coordinates.

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.
            tile_type: Tile type value to set.

        """
        if 0 <= ty < self.height and 0 <= tx < self.width:
            self.tiles[ty][tx] = tile_type

    def is_solid(self, tx: int, ty: int) -> bool:
        """Check if tile is solid (has collision).

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.

        Returns:
            True if tile is solid, False otherwise.

        """
        return self.get_tile(tx, ty) > 0

    def world_to_tile(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to tile coordinates.

        Args:
            x: World X coordinate.
            y: World Y coordinate.

        Returns:
            Tuple of (tile_x, tile_y).

        """
        return int(x // TILE_SIZE), int(y // TILE_SIZE)

    def tile_to_world(self, tx: int, ty: int) -> tuple[float, float]:
        """Convert tile coordinates to world coordinates (center of tile).

        Args:
            tx: Tile X coordinate.
            ty: Tile Y coordinate.

        Returns:
            Tuple of (world_x, world_y) at tile center.

        """
        return (tx * TILE_SIZE + TILE_SIZE / 2, ty * TILE_SIZE + TILE_SIZE / 2)

    def get_pixel_size(self) -> tuple[int, int]:
        """Get map size in pixels.

        Returns:
            Tuple of (width_pixels, height_pixels).

        """
        return self.width * TILE_SIZE, self.height * TILE_SIZE

    def add_spawn_point(self, x: float, y: float, team: int = 0) -> None:
        """Add a spawn point for tanks.

        Args:
            x: World X coordinate.
            y: World Y coordinate.
            team: Team number for this spawn point.

        """
        self.spawn_points.append({"x": x, "y": y, "team": team})

    def get_spawn_point(self, index: int = 0) -> tuple[float, float, int] | None:
        """Get a spawn point by index.

        Args:
            index: Index of spawn point to retrieve.

        Returns:
            Tuple of (x, y, team) or None if index out of bounds.

        """
        if index < len(self.spawn_points):
            sp = self.spawn_points[index]
            return sp["x"], sp["y"], sp.get("team", 0)
        return None
