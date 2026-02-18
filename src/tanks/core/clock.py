"""Fixed timestep clock for deterministic physics."""

import time


class FixedClock:
    """Fixed timestep clock for deterministic game updates.

    Separates rendering from physics updates to ensure consistent gameplay
    regardless of frame rate.
    """

    def __init__(self, ticks_per_second: int = 30) -> None:
        """Initialize the clock.

        Args:
            ticks_per_second: Number of physics updates per second

        """
        self.tps = ticks_per_second
        self.dt = 1.0 / ticks_per_second  # Delta time per tick

        self.accumulator = 0.0
        self.last_time = time.time()

        self.frame_count = 0
        self.fps = 0
        self.fps_timer = 0.0

    def tick(self) -> int:
        """Update clock and return number of fixed updates to perform.

        Returns:
            Number of physics updates to run this frame

        """
        current_time = time.time()
        frame_time = current_time - self.last_time
        self.last_time = current_time

        # Cap frame time to prevent spiral of death
        frame_time = min(frame_time, 0.25)

        self.accumulator += frame_time

        # Calculate FPS
        self.frame_count += 1
        self.fps_timer += frame_time
        if self.fps_timer >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.fps_timer = 0

        # Return number of fixed updates to perform
        updates = 0
        while self.accumulator >= self.dt:
            self.accumulator -= self.dt
            updates += 1

        return updates

    def get_delta_time(self) -> float:
        """Get fixed delta time.

        Returns:
            Fixed time step in seconds

        """
        return self.dt

    def get_fps(self) -> int:
        """Get current FPS.

        Returns:
            Frames per second

        """
        return self.fps
