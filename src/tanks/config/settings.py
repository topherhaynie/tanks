"""Runtime settings that can be modified during gameplay."""


class Settings:
    """Mutable game settings."""

    def __init__(self):
        # Display
        self.fullscreen = False
        self.vsync = True

        # Debug
        self.show_hitboxes = False
        self.show_vision = False  # Show vision and radar ranges
        self.show_vision_cones = False
        self.show_radar = False
        self.show_radar_blips = (
            True  # Show radar detection blips (always on by default)
        )
        self.show_minimap = True  # Show minimap with radar overlay
        self.show_fps = True
        self.show_entity_info = False
        self.show_stats = False  # Show live performance stats overlay

        # Game
        self.paused = False
        self.god_mode = False

    def toggle_debug_overlay(self):
        """Toggle all debug visualizations."""
        all_on = (
            self.show_hitboxes
            and self.show_vision_cones
            and self.show_radar
            and self.show_entity_info
        )

        self.show_hitboxes = not all_on
        self.show_vision_cones = not all_on
        self.show_radar = not all_on
        self.show_entity_info = not all_on
