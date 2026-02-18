"""Terrain memory system for fog of war."""

from tanks.config.constants import FOG_TILE_SIZE, TILE_SIZE


class TerrainMemory:
    """Stores which fog tiles have been revealed by a tank."""

    def __init__(self, map_width: int, map_height: int) -> None:
        """Initialize terrain memory.

        Args:
            map_width: Width of the map in game tiles.
            map_height: Height of the map in game tiles.

        """
        # Calculate fog grid size (smaller tiles for more detail)
        self.fog_width = (map_width * TILE_SIZE) // FOG_TILE_SIZE
        self.fog_height = (map_height * TILE_SIZE) // FOG_TILE_SIZE

        # 2D grid of booleans - True if fog tile has been revealed
        self.revealed: list[list[bool]] = [[False for _ in range(self.fog_width)] for _ in range(self.fog_height)]

    def reveal_tile(self, tx: int, ty: int) -> None:
        """Mark a fog tile as revealed.

        Args:
            tx: Fog tile X coordinate.
            ty: Fog tile Y coordinate.

        """
        if 0 <= tx < self.fog_width and 0 <= ty < self.fog_height:
            self.revealed[ty][tx] = True

    def is_revealed(self, tx: int, ty: int) -> bool:
        """Check if a fog tile has been revealed.

        Args:
            tx: Fog tile X coordinate.
            ty: Fog tile Y coordinate.

        Returns:
            True if fog tile is revealed, False otherwise.

        """
        if 0 <= tx < self.fog_width and 0 <= ty < self.fog_height:
            return self.revealed[ty][tx]
        return False

    def reveal_area(self, tx: int, ty: int, radius_tiles: int) -> None:
        """Reveal all fog tiles in a circular area.

        Args:
            tx: Center fog tile X coordinate.
            ty: Center fog tile Y coordinate.
            radius_tiles: Radius in fog tiles.

        """
        for y in range(max(0, ty - radius_tiles), min(self.fog_height, ty + radius_tiles + 1)):
            for x in range(max(0, tx - radius_tiles), min(self.fog_width, tx + radius_tiles + 1)):
                # Check if within circular radius
                dist_sq = (x - tx) ** 2 + (y - ty) ** 2
                if dist_sq <= radius_tiles**2:
                    self.revealed[y][x] = True
