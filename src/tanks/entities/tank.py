"""Tank entity."""

import math

from tanks.config.constants import SHOOT_COOLDOWN, TANK_MAX_HP, TANK_RADIUS
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
        self.team = team

        # Control (for bots/players)
        self.controller = None  # Will be set to keyboard controller or bot

        # Perception (filled by perception system)
        self.visible_entities = []
        self.fog_memory = None

    def update(self, dt: float) -> None:
        """Update tank state.

        Args:
            dt: Time delta in seconds.

        """
        # Update cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt

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
