"""Sprite management system (for asset integration)."""


class SpriteManager:
    """Manages sprite loading and rendering (Phase 1: placeholder)."""

    def __init__(self):
        self.sprites = {}

    def load_sprite(self, name, filepath):
        """Load a sprite from file."""
        # TODO: Load actual sprite file

    def get_sprite(self, name):
        """Get a loaded sprite."""
        return self.sprites.get(name)
