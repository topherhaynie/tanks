"""Camera system for view management."""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.entities.tank import Tank
    from tanks.maps.map import Map


class CameraMode(Enum):
    """Camera operation modes."""

    FOLLOW = "follow"  # Follow a specific tank smoothly
    GLOBAL = "global"  # Show entire map (fixed, no movement)
    FREE = "free"  # Manual pan and zoom control


class Camera:
    """Camera for scrolling view with multiple modes."""

    def __init__(self, width: int, height: int) -> None:
        """Initialize camera.

        Args:
            width: Viewport width in pixels.
            height: Viewport height in pixels.

        """
        self.viewport_width = width
        self.viewport_height = height

        # Camera position (top-left corner of viewport in world space)
        self.x: float = 0.0
        self.y: float = 0.0

        # Zoom level (1.0 = normal, 2.0 = 2x zoom in, 0.5 = 2x zoom out)
        self.zoom: float = 1.0
        self.min_zoom: float = 0.5
        self.max_zoom: float = 2.0

        # Camera mode
        self.mode: CameraMode = CameraMode.GLOBAL
        self.follow_target: Tank | None = None

        # Smooth follow parameters
        self.follow_smoothing: float = 0.1  # 0 = instant, 1 = no follow

        # Map boundaries (set when map loads)
        self.map_width: float = width
        self.map_height: float = height
        self.bounds_enabled: bool = True

    def set_mode(self, mode: CameraMode) -> None:
        """Set camera operation mode.

        Args:
            mode: New camera mode.

        """
        self.mode = mode

    def set_follow_target(self, tank: "Tank | None") -> None:
        """Set which tank to follow in FOLLOW mode.

        Args:
            tank: Tank to follow, or None to stop following.

        """
        self.follow_target = tank
        if tank and self.mode == CameraMode.FOLLOW:
            # Immediately center on target when first set
            self.center_on(tank.x, tank.y)

    def set_map_bounds(self, game_map: "Map") -> None:
        """Set camera bounds from map dimensions.

        Args:
            game_map: Map to get bounds from.

        """
        map_width_px, map_height_px = game_map.get_pixel_size()
        self.map_width = map_width_px
        self.map_height = map_height_px

    def center_on(self, world_x: float, world_y: float) -> None:
        """Instantly center camera on world coordinates.

        Args:
            world_x: World X coordinate to center on.
            world_y: World Y coordinate to center on.

        """
        self.x = world_x - (self.viewport_width / self.zoom) / 2
        self.y = world_y - (self.viewport_height / self.zoom) / 2
        self._clamp_to_bounds()

    def pan(self, dx: float, dy: float) -> None:
        """Pan camera by delta (for FREE mode).

        Args:
            dx: Delta X in pixels.
            dy: Delta Y in pixels.

        """
        if self.mode == CameraMode.FREE:
            self.x += dx / self.zoom
            self.y += dy / self.zoom
            self._clamp_to_bounds()

    def adjust_zoom(self, delta: float) -> None:
        """Adjust zoom level (for FREE mode).

        Args:
            delta: Zoom delta (positive = zoom in, negative = zoom out).

        """
        if self.mode == CameraMode.FREE:
            old_zoom = self.zoom
            self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom + delta))

            # Adjust position to zoom toward center of viewport
            if self.zoom != old_zoom:
                center_x = self.x + (self.viewport_width / old_zoom) / 2
                center_y = self.y + (self.viewport_height / old_zoom) / 2
                self.x = center_x - (self.viewport_width / self.zoom) / 2
                self.y = center_y - (self.viewport_height / self.zoom) / 2
                self._clamp_to_bounds()

    def update(self, dt: float) -> None:
        """Update camera position based on mode.

        Args:
            dt: Delta time in seconds.

        """
        if (
            self.mode == CameraMode.FOLLOW
            and self.follow_target
            and self.follow_target.active
        ):
            # Smooth follow
            target_x = self.follow_target.x - (self.viewport_width / self.zoom) / 2
            target_y = self.follow_target.y - (self.viewport_height / self.zoom) / 2

            # Interpolate toward target
            self.x += (target_x - self.x) * (1 - self.follow_smoothing)
            self.y += (target_y - self.y) * (1 - self.follow_smoothing)
            self._clamp_to_bounds()

        elif self.mode == CameraMode.GLOBAL:
            # Center on entire map
            map_center_x = self.map_width / 2
            map_center_y = self.map_height / 2

            # Calculate zoom to fit entire map in viewport
            zoom_x = self.viewport_width / self.map_width
            zoom_y = self.viewport_height / self.map_height
            self.zoom = min(zoom_x, zoom_y)

            # Center camera on map
            self.x = map_center_x - (self.viewport_width / self.zoom) / 2
            self.y = map_center_y - (self.viewport_height / self.zoom) / 2

    def _clamp_to_bounds(self) -> None:
        """Clamp camera position to map boundaries."""
        if not self.bounds_enabled:
            return

        # Calculate visible area size
        visible_width = self.viewport_width / self.zoom
        visible_height = self.viewport_height / self.zoom

        # If viewport is larger than map, center on map
        if visible_width >= self.map_width:
            self.x = (self.map_width - visible_width) / 2
        else:
            # Clamp to map edges
            self.x = max(0, min(self.x, self.map_width - visible_width))

        if visible_height >= self.map_height:
            self.y = (self.map_height - visible_height) / 2
        else:
            # Clamp to map edges
            self.y = max(0, min(self.y, self.map_height - visible_height))

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates.

        Args:
            world_x: World X coordinate.
            world_y: World Y coordinate.

        Returns:
            Tuple of (screen_x, screen_y).

        """
        screen_x = (world_x - self.x) * self.zoom
        screen_y = (world_y - self.y) * self.zoom
        return screen_x, screen_y

    def screen_to_world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates.

        Args:
            screen_x: Screen X coordinate.
            screen_y: Screen Y coordinate.

        Returns:
            Tuple of (world_x, world_y).

        """
        world_x = screen_x / self.zoom + self.x
        world_y = screen_y / self.zoom + self.y
        return world_x, world_y

    def is_visible(self, world_x: float, world_y: float, margin: float = 0) -> bool:
        """Check if a world point is visible in viewport.

        Args:
            world_x: World X coordinate.
            world_y: World Y coordinate.
            margin: Extra margin in world units to consider visible.

        Returns:
            True if point is visible (or within margin).

        """
        visible_width = self.viewport_width / self.zoom
        visible_height = self.viewport_height / self.zoom

        return (self.x - margin) <= world_x <= (self.x + visible_width + margin) and (
            self.y - margin
        ) <= world_y <= (self.y + visible_height + margin)
