"""Rendering layers (future expansion)."""

# Placeholder for layer-based rendering system
# Will be expanded in later phases for fog of war, effects, etc.


class Layer:
    """Base rendering layer."""

    def __init__(self, priority=0):
        self.priority = priority
        self.visible = True

    def render(self, screen, game_state):
        """Render this layer."""
