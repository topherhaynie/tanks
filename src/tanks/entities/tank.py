"""Tank entity."""

import math

from tanks.config.constants import (
    MINE_MAX_COUNT,
    MINE_PLACEMENT_COOLDOWN,
    MISSILE_COOLDOWN,
    RADAR_JAMMING_COOLDOWN,
    RADAR_JAMMING_DURATION,
    RADAR_SWEEP_SPEED,
    SHOOT_COOLDOWN,
    TANK_MAX_HP,
    TANK_RADIUS,
)
from tanks.entities.entity import Entity


class Tank(Entity):
    """Tank entity with health, weapons, and sensors."""

    def __init__(self, x: float, y: float, team: int = 0) -> None:
        """Initialize tank entity.

        Args:
            x: Initial X position.
            y: Initial Y position.
            team: Team number (default: 0).

        """
        super().__init__(x, y)

        # Physics
        self.radius = TANK_RADIUS
        self.angle = 0  # Body angle in degrees
        self.turret_angle = 0  # Turret angle (absolute, not relative)

        # Combat
        self.hp = TANK_MAX_HP
        self.max_hp = TANK_MAX_HP
        self.shoot_cooldown = 0
        self.missile_cooldown = 0
        self.mine_cooldown = 0
        self.mine_count = MINE_MAX_COUNT
        self.team = team

        # Control (for bots/players)
        self.controller = None  # Will be set to keyboard controller or bot

        # Perception (filled by perception system)
        self.visible_entities = []
        self.radar_detections = []  # List of (entity, distance, angle)
        self.previous_radar_entities = set()  # Track entities for sound triggers
        self.fog_memory = None

        # Radar sweep and blips
        self.radar_sweep_angle = (
            0.0  # Current angle of radar sweep (clockwise in screen coords)
        )
        self.prev_radar_sweep_angle = (
            0.0  # Previous frame's sweep angle for crossing detection
        )
        # Radar blips store: entity reference, timestamp, angle, snapshot x/y, entity type
        self.radar_blips = []

        # Radar jamming
        self.jamming_active = False  # Is jamming currently active
        self.jamming_timer = 0.0  # Time remaining for active jamming
        self.jamming_cooldown = 0.0  # Cooldown before next jamming use

    def update(self, dt: float) -> None:
        """Update tank state.

        Args:
            dt: Time delta in seconds.

        """
        # Update cooldowns
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt
        if self.missile_cooldown > 0:
            self.missile_cooldown -= dt
        if self.mine_cooldown > 0:
            self.mine_cooldown -= dt

        # Update radar sweep (clockwise in screen coordinates)
        self.prev_radar_sweep_angle = (
            self.radar_sweep_angle
        )  # Store previous for crossing detection
        self.radar_sweep_angle += RADAR_SWEEP_SPEED * dt
        full_circle = 360
        if self.radar_sweep_angle >= full_circle:
            self.radar_sweep_angle -= full_circle
            # Note: prev_angle stays at ~360, current is near 0 - wraparound handled in detection logic

        # Update jamming timers
        if self.jamming_active:
            self.jamming_timer -= dt
            if self.jamming_timer <= 0:
                self.jamming_active = False
                self.jamming_cooldown = RADAR_JAMMING_COOLDOWN

        if self.jamming_cooldown > 0:
            self.jamming_cooldown -= dt

    def take_damage(self, amount: float) -> bool:
        """Take damage and return True if destroyed.

        Args:
            amount: Damage amount to apply.

        Returns:
            True if tank was destroyed, False otherwise.

        """
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.destroy()
            return True
        return False

    def can_shoot(self) -> bool:
        """Check if tank can shoot.

        Returns:
            True if tank can shoot, False if on cooldown.

        """
        return self.shoot_cooldown <= 0

    def shoot(self) -> bool:
        """Trigger shooting (sets cooldown).

        Returns:
            True if shot was fired, False if on cooldown.

        """
        if self.can_shoot():
            self.shoot_cooldown = SHOOT_COOLDOWN
            return True
        return False

    def can_fire_missile(self) -> bool:
        """Check if tank can fire a missile.

        Returns:
            True if tank can fire missile, False if on cooldown.

        """
        return self.missile_cooldown <= 0

    def fire_missile(self) -> bool:
        """Trigger missile fire (sets cooldown).

        Returns:
            True if missile was fired, False if on cooldown.

        """
        if self.can_fire_missile():
            self.missile_cooldown = MISSILE_COOLDOWN
            return True
        return False

    def can_place_mine(self) -> bool:
        """Check if tank can place a mine.

        Returns:
            True if tank has mines left and cooldown is expired.

        """
        return self.mine_count > 0 and self.mine_cooldown <= 0

    def place_mine(self) -> bool:
        """Trigger mine placement (decrements count and sets cooldown).

        Returns:
            True if mine was placed, False if no mines or on cooldown.

        """
        if self.can_place_mine():
            self.mine_count -= 1
            self.mine_cooldown = MINE_PLACEMENT_COOLDOWN
            return True
        return False

    def refill_mines(self) -> None:
        """Refill mines to maximum capacity."""
        self.mine_count = MINE_MAX_COUNT

    def get_turret_tip_position(self) -> tuple[float, float]:
        """Get the position of the turret tip (where bullets spawn).

        Returns:
            Tuple of (x, y) coordinates of turret tip.

        """
        angle_rad = math.radians(self.turret_angle)
        tip_x = self.x + math.cos(angle_rad) * (self.radius + 5)
        tip_y = self.y + math.sin(angle_rad) * (self.radius + 5)
        return tip_x, tip_y

    def is_enemy(self, other_tank: "Tank") -> bool:
        """Check if another tank is an enemy.

        Args:
            other_tank: Another tank entity to check.

        Returns:
            True if other tank is on a different team.

        """
        return self.team != other_tank.team

    def can_jam_radar(self) -> bool:
        """Check if tank can activate radar jamming.

        Returns:
            True if jamming is available, False if on cooldown or already active.

        """
        return not self.jamming_active and self.jamming_cooldown <= 0

    def activate_jamming(self) -> bool:
        """Activate radar jamming.

        Returns:
            True if jamming was activated, False if unavailable.

        """
        if self.can_jam_radar():
            self.jamming_active = True
            self.jamming_timer = RADAR_JAMMING_DURATION
            return True
        return False
