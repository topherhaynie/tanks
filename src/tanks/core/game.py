"""Main game class and game loop."""

import math
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from tanks.config.constants import FPS, TICKS_PER_SECOND, WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from tanks.config.settings import Settings
from tanks.core.clock import FixedClock
from tanks.core.events import EventSystem
from tanks.entities import Bullet, Tank
from tanks.maps import MapLoader
from tanks.physics import CollisionSystem, MovementSystem, ProjectileSystem
from tanks.rendering import Renderer

if TYPE_CHECKING:
    from tanks.input.keyboard import KeyboardController


class GameState:
    """Container for game state."""

    def __init__(self) -> None:
        """Initialize game state."""
        self.tanks: list[Tank] = []
        self.bullets: list[Bullet] = []
        self.game_map = None
        self.fps: float = 0
        self.running: bool = True


class Game:
    """Main game class coordinating all systems."""

    def __init__(self) -> None:
        """Initialize the game."""
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)

        # Core systems
        self.clock = FixedClock(TICKS_PER_SECOND)
        self.render_clock = pygame.time.Clock()  # For FPS limiting
        self.settings = Settings()
        self.events = EventSystem()

        # Game state
        self.state = GameState()

        # Systems
        self.renderer = Renderer(self.screen, self.settings)
        self.collision_system = None  # Created after map loads
        self.movement_system = MovementSystem()
        self.projectile_system = ProjectileSystem()

        # Input handlers
        self.input_handlers: list["KeyboardController"] = []

    def load_map(self, map_name: str | None = None) -> None:
        """Load a game map.

        Args:
            map_name: Name of map file to load, or None for default arena.

        """
        if map_name:
            # Load from file
            map_path = Path(__file__).parent.parent / "maps" / "data" / f"{map_name}.json"
            self.state.game_map = MapLoader.load_from_file(str(map_path))
        else:
            # Create simple arena (20 tiles wide x 11 tiles tall = 1280x704 pixels)
            self.state.game_map = MapLoader.create_simple_arena(20, 11)

        self.collision_system = CollisionSystem(self.state.game_map)

    def spawn_tank(self, spawn_index: int = 0) -> Tank | None:
        """Spawn a tank at a spawn point.

        Args:
            spawn_index: Index of spawn point to use.

        Returns:
            Spawned tank or None if spawn point not found.

        """
        spawn_data = self.state.game_map.get_spawn_point(spawn_index)
        if spawn_data:
            x, y, team = spawn_data
            tank = Tank(x, y, team)
            self.state.tanks.append(tank)
            return tank
        return None

    def add_input_handler(self, handler: "KeyboardController") -> None:
        """Add an input handler for a tank.

        Args:
            handler: Keyboard controller to add.

        """
        self.input_handlers.append(handler)

    def run(self) -> None:
        """Run the main game loop."""
        self.state.running = True

        while self.state.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state.running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)

            # Fixed timestep updates
            num_updates = self.clock.tick()
            dt = self.clock.get_delta_time()

            for _ in range(num_updates):
                self.update(dt)

            # Render
            self.state.fps = self.clock.get_fps()
            self.renderer.render_frame(self.state)

            # Limit rendering FPS
            self.render_clock.tick(FPS)

        pygame.quit()

    def update(self, dt: float) -> None:
        """Update game state.

        Args:
            dt: Time delta in seconds.

        """
        if self.settings.paused:
            return

        # Process input handlers
        for handler in self.input_handlers:
            handler.update(dt)

        # Update tanks
        for tank in self.state.tanks:
            tank.update(dt)

        # Update bullets
        for bullet in self.state.bullets[:]:
            bullet.update(dt)

            # Check wall collisions
            hit_wall, normal = self.collision_system.check_bullet_wall_collision(bullet)
            if hit_wall and not self.projectile_system.bounce_bullet(bullet, normal[0], normal[1]):
                bullet.destroy()

            # Check tank collisions
            hit_tank = self.collision_system.check_bullet_tank_collision(
                bullet,
                self.state.tanks,
            )
            if hit_tank:
                hit_tank.take_damage(bullet.damage)
                bullet.destroy()

            # Remove inactive bullets
            if not bullet.active:
                self.state.bullets.remove(bullet)

        # Handle tank collisions
        for i, tank1 in enumerate(self.state.tanks):
            # Wall collisions
            self.collision_system.check_tank_wall_collision(tank1, self.state.game_map)

            # Tank-tank collisions
            for tank2 in self.state.tanks[i + 1 :]:
                self.collision_system.check_tank_tank_collision(tank1, tank2)

    def shoot_bullet(self, tank: Tank) -> Bullet | None:
        """Create a bullet from a tank.

        Args:
            tank: Tank that is shooting.

        Returns:
            Created bullet or None if on cooldown.

        """
        if tank.shoot():
            tip_x, tip_y = tank.get_turret_tip_position()

            angle_rad = math.radians(tank.turret_angle)
            vx = math.cos(angle_rad) * 400  # Bullet speed
            vy = math.sin(angle_rad) * 400

            bullet = Bullet(tip_x, tip_y, vx, vy, tank.id)
            self.state.bullets.append(bullet)
            return bullet
        return None

    def _handle_keydown(self, key: int) -> None:
        """Handle global key presses.

        Args:
            key: Pygame key code.

        """
        if key == pygame.K_ESCAPE:
            self.state.running = False
        elif key == pygame.K_F1:
            self.settings.toggle_debug_overlay()
        elif key == pygame.K_F2:
            self.settings.show_hitboxes = not self.settings.show_hitboxes
        elif key == pygame.K_p:
            self.settings.paused = not self.settings.paused
