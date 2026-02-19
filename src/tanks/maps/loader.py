"""Map loader for loading maps from files."""

import json

from ..config.constants import (
    TILE_EMPTY,
    TILE_SIZE,
    TILE_WALL_DIAGONAL_NE,
    TILE_WALL_DIAGONAL_NW,
    TILE_WALL_HORIZONTAL,
    TILE_WALL_SOLID,
    TILE_WALL_VERTICAL,
)
from .map import Map


class MapLoader:
    """Load maps from JSON files."""

    TILE_CHARS = {
        ".": TILE_EMPTY,
        "-": TILE_WALL_HORIZONTAL,
        "|": TILE_WALL_VERTICAL,
        "/": TILE_WALL_DIAGONAL_NE,
        "\\": TILE_WALL_DIAGONAL_NW,
        "#": TILE_WALL_SOLID,
    }

    @staticmethod
    def load_from_file(filepath):
        """Load map from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        return MapLoader.load_from_dict(data)

    @staticmethod
    def load_from_dict(data):
        """Load map from dictionary."""
        width = data["width"]
        height = data["height"]

        # Parse tile data
        if "tiles" in data:
            tiles = data["tiles"]
        elif "tile_string" in data:
            tiles = MapLoader._parse_tile_string(data["tile_string"])
        else:
            tiles = None

        game_map = Map(width, height, tiles)

        # Load spawn points
        if "spawn_points" in data:
            for sp in data["spawn_points"]:
                game_map.add_spawn_point(
                    sp["x"],
                    sp["y"],
                    sp.get("team", 0),
                )

        return game_map

    @staticmethod
    def _parse_tile_string(tile_string):
        """Parse ASCII tile representation."""
        lines = tile_string.strip().split("\n")
        tiles = []

        for line in lines:
            row = []
            for char in line:
                tile_type = MapLoader.TILE_CHARS.get(char, TILE_EMPTY)
                row.append(tile_type)
            tiles.append(row)

        return tiles

    @staticmethod
    def create_simple_arena(width=20, height=11):
        """Create a simple arena map with walls around the edges."""
        tiles = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]

        # Add border walls
        for i in range(width):
            tiles[0][i] = TILE_WALL_SOLID
            tiles[height - 1][i] = TILE_WALL_SOLID
        for i in range(height):
            tiles[i][0] = TILE_WALL_SOLID
            tiles[i][width - 1] = TILE_WALL_SOLID

        # Add some interior obstacles for interest
        # Small wall clusters
        if width >= 10 and height >= 6:
            tiles[3][4] = TILE_WALL_SOLID
            tiles[3][5] = TILE_WALL_SOLID
            tiles[3][width - 5] = TILE_WALL_SOLID
            tiles[3][width - 6] = TILE_WALL_SOLID

            tiles[height - 4][4] = TILE_WALL_SOLID
            tiles[height - 4][5] = TILE_WALL_SOLID
            tiles[height - 4][width - 5] = TILE_WALL_SOLID
            tiles[height - 4][width - 6] = TILE_WALL_SOLID

        game_map = Map(width, height, tiles)

        # Add spawn points (3 points for multi-bot battles)
        center_x = width * TILE_SIZE // 2
        center_y = height * TILE_SIZE // 2
        offset = TILE_SIZE * 3
        game_map.add_spawn_point(center_x - offset, center_y, team=0)
        game_map.add_spawn_point(center_x + offset, center_y, team=1)
        game_map.add_spawn_point(
            center_x, center_y - offset, team=2
        )  # Third spawn point

        return game_map
