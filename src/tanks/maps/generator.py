"""Procedural map generation with configurable parameters."""

# ruff: noqa: PLR2004, S311
# PLR2004: Magic constants are acceptable for map generation parameters
# S311: random module is fine for non-cryptographic game generation

import random
from dataclasses import dataclass
from enum import Enum

from tanks.config.constants import TILE_SIZE, TILE_WALL_SOLID
from tanks.maps.map import Map


class MapSize(Enum):
    """Predefined map sizes."""

    SMALL = (20, 11)  # 1280x704 px - original arena size
    MEDIUM = (40, 22)  # 2560x1408 px - 2x original
    LARGE = (60, 34)  # 3840x2176 px - 3x original
    HUGE = (80, 45)  # 5120x2880 px - 4x original


class TerrainPattern(Enum):
    """Terrain generation patterns."""

    OPEN_ARENA = "open_arena"  # Minimal obstacles, mostly open space
    SCATTERED = "scattered"  # Random scattered obstacles
    MAZE = "maze"  # Dense maze-like corridors
    ROOMS = "rooms"  # Connected rooms with corridors
    CORRIDORS = "corridors"  # Long corridors with intersections
    FORTRESS = "fortress"  # Central structure with outer walls


@dataclass
class GeneratorConfig:
    """Configuration for map generation."""

    width: int = 20
    height: int = 11
    pattern: TerrainPattern = TerrainPattern.OPEN_ARENA
    obstacle_density: float = 0.15  # 0-1, fraction of tiles with obstacles
    border_walls: bool = True  # Add walls around map perimeter
    min_open_space: float = 0.6  # Minimum fraction of reachable tiles
    num_spawn_points: int = 2  # Number of spawn points to generate
    spawn_teams: list[int] | None = None  # Team assignments, auto if None
    seed: int | None = None  # Random seed for reproducibility
    symmetry: bool = False  # Generate symmetric maps for fairness


class MapGenerator:
    """Generate procedural maps with various patterns."""

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        """Initialize map generator.

        Args:
            config: Generator configuration (uses defaults if None).

        """
        self.config = config or GeneratorConfig()
        if self.config.seed is not None:
            random.seed(self.config.seed)

    def generate(self) -> Map:
        """Generate a new map based on configuration.

        Returns:
            Generated map with spawn points.

        """
        # Create empty map
        game_map = Map(self.config.width, self.config.height)

        # Add border walls if requested
        if self.config.border_walls:
            self._add_border_walls(game_map)

        # Generate terrain based on pattern
        if self.config.pattern == TerrainPattern.OPEN_ARENA:
            self._generate_open_arena(game_map)
        elif self.config.pattern == TerrainPattern.SCATTERED:
            self._generate_scattered(game_map)
        elif self.config.pattern == TerrainPattern.MAZE:
            self._generate_maze(game_map)
        elif self.config.pattern == TerrainPattern.ROOMS:
            self._generate_rooms(game_map)
        elif self.config.pattern == TerrainPattern.CORRIDORS:
            self._generate_corridors(game_map)
        elif self.config.pattern == TerrainPattern.FORTRESS:
            self._generate_fortress(game_map)

        # Apply symmetry if requested
        if self.config.symmetry:
            self._apply_symmetry(game_map)

        # Generate spawn points with balanced positioning
        self._generate_spawn_points(game_map)

        # Validate map (ensure reachability)
        if not self._validate_map(game_map):
            # If validation fails, regenerate with more open space
            self.config.obstacle_density *= 0.8
            return self.generate()

        return game_map

    def _add_border_walls(self, game_map: Map) -> None:
        """Add walls around map perimeter.

        Args:
            game_map: Map to add borders to.

        """
        # Top and bottom walls
        for x in range(game_map.width):
            game_map.set_tile(x, 0, TILE_WALL_SOLID)
            game_map.set_tile(x, game_map.height - 1, TILE_WALL_SOLID)

        # Left and right walls
        for y in range(game_map.height):
            game_map.set_tile(0, y, TILE_WALL_SOLID)
            game_map.set_tile(game_map.width - 1, y, TILE_WALL_SOLID)

    def _generate_open_arena(self, game_map: Map) -> None:
        """Generate an open arena with minimal obstacles.

        Args:
            game_map: Map to generate terrain in.

        """
        # Add a few scattered obstacles
        density = min(0.08, self.config.obstacle_density)
        self._add_random_obstacles(game_map, density)

        # Add some cover structures
        num_cover = int((game_map.width * game_map.height) / 200)
        for _ in range(num_cover):
            self._add_cover_cluster(game_map)

    def _generate_scattered(self, game_map: Map) -> None:
        """Generate scattered random obstacles.

        Args:
            game_map: Map to generate terrain in.

        """
        self._add_random_obstacles(game_map, self.config.obstacle_density)

        # Add some obstacle clusters for variety
        num_clusters = int((game_map.width * game_map.height) / 150)
        for _ in range(num_clusters):
            self._add_obstacle_cluster(game_map, size=random.randint(2, 4))

    def _generate_maze(self, game_map: Map) -> None:
        """Generate maze-like corridors.

        Args:
            game_map: Map to generate terrain in.

        """
        # Use recursive division algorithm
        self._recursive_divide(
            game_map,
            2 if self.config.border_walls else 0,
            2 if self.config.border_walls else 0,
            game_map.width - (3 if self.config.border_walls else 1),
            game_map.height - (3 if self.config.border_walls else 1),
        )

    def _generate_rooms(self, game_map: Map) -> None:
        """Generate connected rooms with corridors.

        Args:
            game_map: Map to generate terrain in.

        """
        # Determine room grid
        room_w = game_map.width // 4
        room_h = game_map.height // 3

        # Generate rooms in a grid
        for ry in range(2, 3):  # 2 rows of rooms
            for rx in range(3, 4):  # 3 columns of rooms
                room_x = rx * room_w + random.randint(-2, 2)
                room_y = ry * room_h + random.randint(-2, 2)
                room_width = random.randint(room_w // 2, room_w - 2)
                room_height = random.randint(room_h // 2, room_h - 2)

                self._add_room(game_map, room_x, room_y, room_width, room_height)

        # Connect rooms with corridors
        self._connect_rooms(game_map)

    def _generate_corridors(self, game_map: Map) -> None:
        """Generate long corridors with intersections.

        Args:
            game_map: Map to generate terrain in.

        """
        # Add horizontal corridors
        num_h_corridors = game_map.height // 4
        for i in range(num_h_corridors):
            y = (i + 1) * (game_map.height // (num_h_corridors + 1))
            self._add_horizontal_corridor(game_map, y, width=3)

        # Add vertical corridors
        num_v_corridors = game_map.width // 6
        for i in range(num_v_corridors):
            x = (i + 1) * (game_map.width // (num_v_corridors + 1))
            self._add_vertical_corridor(game_map, x, width=3)

        # Fill remaining space with obstacles
        self._add_random_obstacles(game_map, self.config.obstacle_density * 0.8)

    def _generate_fortress(self, game_map: Map) -> None:
        """Generate a central fortress structure.

        Args:
            game_map: Map to generate terrain in.

        """
        center_x = game_map.width // 2
        center_y = game_map.height // 2

        # Outer walls
        fortress_w = min(game_map.width // 3, game_map.height // 2)
        fortress_h = fortress_w // 2

        for x in range(center_x - fortress_w, center_x + fortress_w):
            if 0 < x < game_map.width - 1:
                game_map.set_tile(x, center_y - fortress_h, TILE_WALL_SOLID)
                game_map.set_tile(x, center_y + fortress_h, TILE_WALL_SOLID)

        for y in range(center_y - fortress_h, center_y + fortress_h):
            if 0 < y < game_map.height - 1:
                game_map.set_tile(center_x - fortress_w, y, TILE_WALL_SOLID)
                game_map.set_tile(center_x + fortress_w, y, TILE_WALL_SOLID)

        # Add openings
        game_map.set_tile(center_x, center_y - fortress_h, 0)
        game_map.set_tile(center_x, center_y + fortress_h, 0)
        game_map.set_tile(center_x - fortress_w, center_y, 0)
        game_map.set_tile(center_x + fortress_w, center_y, 0)

        # Add scattered cover outside
        self._add_random_obstacles(game_map, self.config.obstacle_density * 0.5)

    def _add_random_obstacles(self, game_map: Map, density: float) -> None:
        """Add random obstacles across the map.

        Args:
            game_map: Map to add obstacles to.
            density: Fraction of tiles to fill (0-1).

        """
        num_obstacles = int(game_map.width * game_map.height * density)

        for _ in range(num_obstacles):
            x = random.randint(1, game_map.width - 2)
            y = random.randint(1, game_map.height - 2)

            if game_map.get_tile(x, y) == 0:
                game_map.set_tile(x, y, TILE_WALL_SOLID)

    def _add_cover_cluster(self, game_map: Map) -> None:
        """Add a small cluster of tiles for cover.

        Args:
            game_map: Map to add cover to.

        """
        x = random.randint(2, game_map.width - 3)
        y = random.randint(2, game_map.height - 3)

        # 2x2 or 3x2 cluster
        width = random.choice([2, 3])
        for dx in range(width):
            for dy in range(2):
                if game_map.get_tile(x + dx, y + dy) == 0:
                    game_map.set_tile(x + dx, y + dy, TILE_WALL_SOLID)

    def _add_obstacle_cluster(self, game_map: Map, size: int) -> None:
        """Add a cluster of obstacles.

        Args:
            game_map: Map to add cluster to.
            size: Radius of cluster.

        """
        center_x = random.randint(size, game_map.width - size - 1)
        center_y = random.randint(size, game_map.height - size - 1)

        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                if random.random() < 0.6:  # Sparse cluster
                    x, y = center_x + dx, center_y + dy
                    if (
                        1 <= x < game_map.width - 1
                        and 1 <= y < game_map.height - 1
                        and game_map.get_tile(x, y) == 0
                    ):
                        game_map.set_tile(x, y, TILE_WALL_SOLID)

    def _add_room(
        self,
        game_map: Map,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Add a room with walls.

        Args:
            game_map: Map to add room to.
            x: Room top-left X.
            y: Room top-left Y.
            width: Room width.
            height: Room height.

        """
        # Fill room with walls
        for dx in range(width):
            for dy in range(height):
                rx, ry = x + dx, y + dy
                if 1 <= rx < game_map.width - 1 and 1 <= ry < game_map.height - 1:
                    game_map.set_tile(rx, ry, TILE_WALL_SOLID)

        # Clear interior
        for dx in range(2, width - 2):
            for dy in range(2, height - 2):
                rx, ry = x + dx, y + dy
                if 1 <= rx < game_map.width - 1 and 1 <= ry < game_map.height - 1:
                    game_map.set_tile(rx, ry, 0)

    def _connect_rooms(self, game_map: Map) -> None:
        """Connect rooms with corridors.

        Args:
            game_map: Map with rooms to connect.

        """
        # Simple implementation: clear some paths
        for _ in range(game_map.width // 3):
            x = random.randint(2, game_map.width - 3)
            for y in range(1, game_map.height - 1):
                if random.random() < 0.3:
                    game_map.set_tile(x, y, 0)

    def _add_horizontal_corridor(self, game_map: Map, y: int, width: int) -> None:
        """Add a horizontal corridor.

        Args:
            game_map: Map to add corridor to.
            y: Y position of corridor.
            width: Corridor width (height).

        """
        for x in range(1, game_map.width - 1):
            for dy in range(width):
                cy = y + dy - width // 2
                if 1 <= cy < game_map.height - 1:
                    game_map.set_tile(x, cy, 0)

    def _add_vertical_corridor(self, game_map: Map, x: int, width: int) -> None:
        """Add a vertical corridor.

        Args:
            game_map: Map to add corridor to.
            x: X position of corridor.
            width: Corridor width.

        """
        for y in range(1, game_map.height - 1):
            for dx in range(width):
                cx = x + dx - width // 2
                if 1 <= cx < game_map.width - 1:
                    game_map.set_tile(cx, y, 0)

    def _recursive_divide(
        self,
        game_map: Map,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Recursive division maze generation.

        Args:
            game_map: Map to generate maze in.
            x: Region top-left X.
            y: Region top-left Y.
            width: Region width.
            height: Region height.

        """
        if width < 4 or height < 4:
            return

        # Choose division axis
        horizontal = height > width or (height == width and random.random() < 0.5)

        if horizontal:
            # Divide horizontally
            wall_y = y + random.randint(2, height - 3)
            gap_x = x + random.randint(0, width - 1)

            for wx in range(x, x + width):
                if wx != gap_x and 1 <= wx < game_map.width - 1:
                    game_map.set_tile(wx, wall_y, TILE_WALL_SOLID)

            self._recursive_divide(game_map, x, y, width, wall_y - y)
            self._recursive_divide(
                game_map, x, wall_y + 1, width, y + height - wall_y - 1
            )
        else:
            # Divide vertically
            wall_x = x + random.randint(2, width - 3)
            gap_y = y + random.randint(0, height - 1)

            for wy in range(y, y + height):
                if wy != gap_y and 1 <= wy < game_map.height - 1:
                    game_map.set_tile(wall_x, wy, TILE_WALL_SOLID)

            self._recursive_divide(game_map, x, y, wall_x - x, height)
            self._recursive_divide(
                game_map, wall_x + 1, y, x + width - wall_x - 1, height
            )

    def _apply_symmetry(self, game_map: Map) -> None:
        """Apply vertical symmetry to map for balance.

        Args:
            game_map: Map to make symmetric.

        """
        mid_x = game_map.width // 2

        for y in range(game_map.height):
            for x in range(mid_x):
                mirror_x = game_map.width - 1 - x
                tile = game_map.get_tile(x, y)
                game_map.set_tile(mirror_x, y, tile)

    def _generate_spawn_points(self, game_map: Map) -> None:
        """Generate balanced spawn points.

        Args:
            game_map: Map to add spawn points to.

        """
        teams = self.config.spawn_teams or list(range(self.config.num_spawn_points))

        if self.config.num_spawn_points == 2:
            # Two spawn points: opposite corners
            positions = [
                (game_map.width * 0.15, game_map.height * 0.15),
                (game_map.width * 0.85, game_map.height * 0.85),
            ]
        elif self.config.num_spawn_points == 3:
            # Three spawn points: triangle formation
            positions = [
                (game_map.width * 0.25, game_map.height * 0.25),
                (game_map.width * 0.75, game_map.height * 0.25),
                (game_map.width * 0.5, game_map.height * 0.75),
            ]
        elif self.config.num_spawn_points == 4:
            # Four spawn points: corners
            positions = [
                (game_map.width * 0.2, game_map.height * 0.2),
                (game_map.width * 0.8, game_map.height * 0.2),
                (game_map.width * 0.2, game_map.height * 0.8),
                (game_map.width * 0.8, game_map.height * 0.8),
            ]
        else:
            # Fallback: distribute around center
            positions = []
            for i in range(self.config.num_spawn_points):
                _ = (2 * 3.14159 * i) / self.config.num_spawn_points  # angle (unused)
                radius = min(game_map.width, game_map.height) * 0.35
                x = game_map.width / 2 + radius * (1 if i % 2 == 0 else -1)
                y = game_map.height / 2 + radius * (
                    1 if i >= self.config.num_spawn_points / 2 else -1
                )
                positions.append((x, y))

        # Convert to pixel coordinates and find clear spots
        for i, (tx, ty) in enumerate(positions[: self.config.num_spawn_points]):
            # Find nearest clear tile
            px, py = self._find_clear_spawn(game_map, int(tx), int(ty))
            team = teams[i] if i < len(teams) else i
            game_map.add_spawn_point(px * TILE_SIZE, py * TILE_SIZE, team)

    def _find_clear_spawn(self, game_map: Map, tx: int, ty: int) -> tuple[int, int]:
        """Find nearest clear tile for spawn point.

        Args:
            game_map: Map to search in.
            tx: Target tile X.
            ty: Target tile Y.

        Returns:
            Tuple of (clear_x, clear_y) in tiles.

        """
        # Search in expanding radius until we find clear tile
        for radius in range(20):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    x, y = tx + dx, ty + dy
                    if 2 <= x < game_map.width - 2 and 2 <= y < game_map.height - 2:
                        # Check if tile and neighbors are clear
                        clear = True
                        for ndx in range(-1, 2):
                            for ndy in range(-1, 2):
                                if game_map.get_tile(x + ndx, y + ndy) != 0:
                                    clear = False
                                    break
                            if not clear:
                                break
                        if clear:
                            # Convert to center of tile
                            return x, y

        # Fallback to center
        return game_map.width // 2, game_map.height // 2

    def _validate_map(self, game_map: Map) -> bool:
        """Validate map has enough reachable space.

        Args:
            game_map: Map to validate.

        Returns:
            True if map is valid.

        """
        # Count reachable tiles from first spawn point
        if not game_map.spawn_points:
            return True

        spawn = game_map.spawn_points[0]
        start_x = int(spawn["x"] // TILE_SIZE)
        start_y = int(spawn["y"] // TILE_SIZE)

        visited = set()
        stack = [(start_x, start_y)]

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            if not (0 <= x < game_map.width and 0 <= y < game_map.height):
                continue
            if game_map.get_tile(x, y) != 0:
                continue

            visited.add((x, y))

            # Check neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((x + dx, y + dy))

        # Check if enough space is reachable
        total_tiles = game_map.width * game_map.height
        reachable_ratio = len(visited) / total_tiles

        return reachable_ratio >= self.config.min_open_space
