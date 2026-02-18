"""Event system for game events."""


class EventSystem:
    """Simple event system for game events."""

    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type, callback):
        """Subscribe to an event type."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def emit(self, event_type, data=None):
        """Emit an event."""
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                callback(data)

    def unsubscribe(self, event_type, callback):
        """Unsubscribe from an event type."""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)


# Event types
EVENT_TANK_DESTROYED = "tank_destroyed"
EVENT_BULLET_FIRED = "bullet_fired"
EVENT_BULLET_HIT = "bullet_hit"
EVENT_GAME_OVER = "game_over"
