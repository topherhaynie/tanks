"""Main game class and game loop."""

import math
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from tanks.config.constants import (
    FPS,
    INPUT_RATE,
    PHYSICS_RATE,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from tanks.config.settings import Settings
from tanks.core.clock import FixedClock
from tanks.core.events import EventSystem
from tanks.core.stats import StatsTracker
from tanks.effects.visual import MuzzleFlash, VisualEffect
from tanks.entities import Bullet, Tank
from tanks.maps import MapLoader
from tanks.perception import RadarSystem, TerrainMemory, VisionSystem
from tanks.physics import CollisionSystem, MovementSystem, ProjectileSystem
from tanks.rendering import Renderer
from tanks.rendering.camera import Camera, CameraMode

try:
    from tanks.audio import SoundManager
except ImportError:
    SoundManager = None  # type: ignore[misc, assignment]

if TYPE_CHECKING:
    from tanks.input.controller import Controller


class GameState:
    """Container for game state."""

    def __init__(self) -> None:
        """Initialize game state."""
        self.tanks: list[Tank] = []
        self.bullets: list[Bullet] = []
        self.effects: list[VisualEffect] = []
        self.game_map = None
        self.fps: float = 0
        self.running: bool = True
        self.quit_app: bool = False  # Signal to quit entire application
        self.stats_tracker = None  # Will be set by Game instance


class Game:
    """Main game class coordinating all systems."""

    def __init__(self) -> None:
        """Initialize the game."""
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)

        # Core systems
        self.clock = FixedClock(PHYSICS_RATE)  # High frequency for physics
        self.input_clock = FixedClock(INPUT_RATE)  # Lower frequency for input
        self.render_clock = pygame.time.Clock()  # For FPS limiting
        self.settings = Settings()
        self.events = EventSystem()

        # Game state
        self.state = GameState()

        # Systems
        self.renderer = Renderer(self.screen, self.settings)
        self.camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.collision_system = None  # Created after map loads
        self.movement_system = MovementSystem()
        self.projectile_system = ProjectileSystem()
        self.sound_manager = SoundManager() if SoundManager else None
        self.vision_system = None  # Created after map loads
        self.radar_system = RadarSystem()
        self.stats_tracker = StatsTracker()

        # Link stats tracker to state for rendering access
        self.state.stats_tracker = self.stats_tracker

        # Input handlers
        self.input_handlers: list[Controller] = []

        # Input tick tracking
        self.input_tick_id = 0

    def load_map(self, map_name: str | None = None) -> None:
        """Load a game map.

        Args:
            map_name: Name of map file to load, or None for default arena.

        """
        if map_name:
            # Load from file
            map_path = (
                Path(__file__).parent.parent / "maps" / "data" / f"{map_name}.json"
            )
            self.state.game_map = MapLoader.load_from_file(str(map_path))
        else:
            # Create simple arena (20 tiles wide x 11 tiles tall = 1280x704 pixels)
            self.state.game_map = MapLoader.create_simple_arena(20, 11)

        self.collision_system = CollisionSystem(self.state.game_map)
        self.vision_system = VisionSystem(self.state.game_map)

        # Set camera bounds
        self.camera.set_map_bounds(self.state.game_map)

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
            # Initialize fog memory for the tank
            tank.fog_memory = TerrainMemory(
                self.state.game_map.width,
                self.state.game_map.height,
            )
            self.state.tanks.append(tank)
            # Register tank for stats tracking
            self.stats_tracker.register_tank(tank)
            return tank
        return None

    def add_input_handler(self, handler: "Controller") -> None:
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
                    self.state.quit_app = True  # Signal complete exit
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)

            # Input updates at lower rate for determinism
            num_input_updates = self.input_clock.tick()
            input_dt = self.input_clock.get_delta_time()
            for _ in range(num_input_updates):
                self.update_input(input_dt)

            # Physics updates at higher rate for accuracy
            num_physics_updates = self.clock.tick()
            physics_dt = self.clock.get_delta_time()
            for _ in range(num_physics_updates):
                self.update_physics(physics_dt)

            # Render
            self.state.fps = self.clock.get_fps()  # Show physics rate

            # Handle camera panning (continuous input)
            self._handle_camera_pan(physics_dt)

            # Update camera position
            self.camera.update(physics_dt)
            self.renderer.render_frame(self.state, self.camera)

            # Limit rendering FPS
            self.render_clock.tick(FPS)

    def update_input(self, dt: float) -> None:
        """Update input handlers at fixed rate for determinism.

        Args:
            dt: Time delta in seconds.

        """
        if self.settings.paused:
            return

        # Process input handlers - sample at lower rate
        self.input_tick_id += 1
        for handler in self.input_handlers:
            handler.update(dt)

    def update_physics(self, dt: float) -> None:
        """Update physics at high rate for accuracy.

        Args:
            dt: Time delta in seconds.

        """
        if self.settings.paused:
            return

        # Update tanks
        for tank in self.state.tanks:
            tank.update(dt)
            # Track survival time and distance
            if tank.active:
                self.stats_tracker.update_survival_time(tank, dt)
                self.stats_tracker.update_distance(tank)

        # Update bullets
        for bullet in self.state.bullets[:]:
            bullet.update(dt)

            # Check wall collisions
            hit_wall, normal = self.collision_system.check_bullet_wall_collision(bullet)
            if hit_wall and not self.projectile_system.bounce_bullet(
                bullet,
                normal[0],
                normal[1],
            ):
                bullet.destroy()
            elif hit_wall:
                # Bullet bounced
                if self.sound_manager:
                    self.sound_manager.play_bounce()

            # Check tank collisions
            hit_tank = self.collision_system.check_bullet_tank_collision(
                bullet,
                self.state.tanks,
            )
            if hit_tank:
                # Find shooter tank for stats
                shooter_tank = next(
                    (t for t in self.state.tanks if t.id == bullet.owner_id),
                    None,
                )

                # Record hit and damage
                if shooter_tank:
                    self.stats_tracker.record_hit(shooter_tank, hit_tank, bullet.damage)

                # Apply damage and check for kill
                was_destroyed = hit_tank.take_damage(bullet.damage)
                if was_destroyed and shooter_tank:
                    self.stats_tracker.record_kill(shooter_tank, hit_tank)

                bullet.destroy()
                if self.sound_manager:
                    self.sound_manager.play_hit()

            # Remove inactive bullets
            if not bullet.active:
                self.state.bullets.remove(bullet)

        # Update visual effects
        for effect in self.state.effects[:]:
            effect.update(dt)
            if not effect.active:
                self.state.effects.remove(effect)

        # Update perception for all active tanks
        self.update_perception()

        # Handle tank collisions
        for i, tank1 in enumerate(self.state.tanks):
            # Wall collisions
            self.collision_system.check_tank_wall_collision(tank1, self.state.game_map)

            # Tank-tank collisions
            for tank2 in self.state.tanks[i + 1 :]:
                self.collision_system.check_tank_tank_collision(tank1, tank2)

    def update_perception(self) -> None:
        """Update vision and radar for all tanks."""
        if not self.vision_system:
            return

        # Collect all entities (tanks + bullets)
        all_entities = list(self.state.tanks) + list(self.state.bullets)

        for tank in self.state.tanks:
            if not tank.active:
                continue

            # Update vision (line of sight)
            tank.visible_entities = self.vision_system.update_vision(tank, all_entities)

            # Reveal terrain visible to tank
            self.vision_system.reveal_visible_terrain(tank)

            # Update radar (not blocked by walls)
            tank.radar_detections = self.radar_system.detect_entities(
                tank,
                all_entities,
            )

            # Check for new radar detections (trigger sound)
            current_radar_entities = {entity for entity, _, _ in tank.radar_detections}
            new_detections = current_radar_entities - tank.previous_radar_entities

            # Play radar ping for new detections (only if not visible)
            if new_detections:
                for entity in new_detections:
                    if entity not in tank.visible_entities:
                        self.sound_manager.play_radar_ping()
                        break  # Only play sound once even if multiple new entities

            tank.previous_radar_entities = current_radar_entities

            # Update radar sweep blips (detect when sweep crosses targets)
            self._update_radar_sweep_blips(tank)

    def _update_radar_sweep_blips(self, tank: Tank) -> None:
        """Update radar blips when sweep crosses detected entities.

        Args:
            tank: Tank whose radar sweep to update.

        """
        import time

        current_time = time.time()

        # Check if sweep crosses any radar-detected entities
        for entity, _distance, angle_deg in tank.radar_detections:
            # Skip if entity is visible (no need for radar blip)
            if entity in tank.visible_entities:
                continue

            # Normalize angles to 0-360
            entity_angle = angle_deg % 360
            current_sweep = tank.radar_sweep_angle % 360
            prev_sweep = tank.prev_radar_sweep_angle % 360

            # Check if sweep JUST CROSSED the entity angle (from prev to current)
            # Handle wraparound at 0/360 degrees
            crossed = False
            if prev_sweep < current_sweep:
                # Normal case: no wraparound
                crossed = prev_sweep <= entity_angle <= current_sweep
            else:
                # Wraparound case: sweep crosses 0
                crossed = entity_angle >= prev_sweep or entity_angle <= current_sweep

            # Add blip if sweep crossed the entity angle
            if crossed:
                # Check if entity already has a recent blip
                has_recent_blip = any(
                    blip_entity == entity and (current_time - blip_time) < 0.5
                    for blip_entity, blip_time, *_ in tank.radar_blips
                )

                if not has_recent_blip:
                    # Capture snapshot at time of detection
                    entity_type = type(entity).__name__
                    tank.radar_blips.append(
                        (
                            entity,
                            current_time,
                            entity_angle,
                            entity.x,
                            entity.y,
                            entity_type,
                        ),
                    )

        # Remove old blips (faded out)
        tank.radar_blips = [
            (entity, blip_time, angle, snap_x, snap_y, entity_type)
            for entity, blip_time, angle, snap_x, snap_y, entity_type in tank.radar_blips
            if (current_time - blip_time) < 2.0 and entity.active  # Keep for 2 seconds
        ]

    def update(self, dt: float) -> None:
        """Legacy update method for backward compatibility.

        Args:
            dt: Time delta in seconds.

        """
        self.update_input(dt)
        self.update_physics(dt)

    def shoot_bullet(self, tank: Tank) -> Bullet | None:
        """Create a bullet from a tank.

        Args:
            tank: Tank that is shooting.

        Returns:
            Created bullet or None if on cooldown.

        """
        if tank.shoot():
            # Record shot fired
            self.stats_tracker.record_shot(tank)

            tip_x, tip_y = tank.get_turret_tip_position()

            angle_rad = math.radians(tank.turret_angle)
            vx = math.cos(angle_rad) * 400  # Bullet speed
            vy = math.sin(angle_rad) * 400

            bullet = Bullet(tip_x, tip_y, vx, vy, tank.id)
            self.state.bullets.append(bullet)

            # Create muzzle flash effect
            muzzle_flash = MuzzleFlash(tip_x, tip_y, tank.turret_angle)
            self.state.effects.append(muzzle_flash)

            # Play shoot sound
            if self.sound_manager:
                self.sound_manager.play_shoot()

            return bullet
        return None

    def display_final_stats(self) -> None:
        """Display final match statistics summary."""
        self.stats_tracker.print_summary()

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
        elif key == pygame.K_F3:
            self.settings.show_vision = not self.settings.show_vision
        elif key == pygame.K_F4:
            self.settings.show_radar_blips = not self.settings.show_radar_blips
        elif key == pygame.K_F5:
            self.settings.show_minimap = not self.settings.show_minimap
        elif key == pygame.K_F6:
            self.settings.show_stats = not self.settings.show_stats
        elif key == pygame.K_p:
            self.settings.paused = not self.settings.paused
        elif key == pygame.K_c:
            # Cycle camera modes
            self._cycle_camera_mode()
        elif key == pygame.K_TAB:
            # Cycle follow target
            self._cycle_follow_target()
        elif key == pygame.K_EQUALS or key == pygame.K_PLUS:
            # Zoom in (FREE mode)
            self.camera.adjust_zoom(0.1)
        elif key == pygame.K_MINUS:
            # Zoom out (FREE mode)
            self.camera.adjust_zoom(-0.1)

    def _cycle_camera_mode(self) -> None:
        """Cycle through camera modes."""
        if self.camera.mode == CameraMode.GLOBAL:
            self.camera.set_mode(CameraMode.FOLLOW)
            # Set follow target to first active tank if available
            if self.state.tanks:
                active_tanks = [t for t in self.state.tanks if t.active]
                if active_tanks:
                    self.camera.set_follow_target(active_tanks[0])
        elif self.camera.mode == CameraMode.FOLLOW:
            self.camera.set_mode(CameraMode.FREE)
            self.camera.set_follow_target(None)
        else:  # FREE
            self.camera.set_mode(CameraMode.GLOBAL)
            self.camera.set_follow_target(None)

    def _cycle_follow_target(self) -> None:
        """Cycle to next active tank as follow target."""
        if self.camera.mode != CameraMode.FOLLOW:
            return

        active_tanks = [t for t in self.state.tanks if t.active]
        if not active_tanks:
            return

        current_target = self.camera.follow_target
        if current_target not in active_tanks:
            self.camera.set_follow_target(active_tanks[0])
        else:
            current_index = active_tanks.index(current_target)
            next_index = (current_index + 1) % len(active_tanks)
            self.camera.set_follow_target(active_tanks[next_index])

    def _handle_camera_pan(self, dt: float) -> None:
        """Handle camera panning with arrow keys in FREE mode.

        Args:
            dt: Delta time in seconds.

        """
        if self.camera.mode != CameraMode.FREE:
            return

        keys = pygame.key.get_pressed()
        pan_speed = 300  # pixels per second

        dx = 0
        dy = 0

        if keys[pygame.K_LEFT]:
            dx -= pan_speed * dt
        if keys[pygame.K_RIGHT]:
            dx += pan_speed * dt
        if keys[pygame.K_UP]:
            dy -= pan_speed * dt
        if keys[pygame.K_DOWN]:
            dy += pan_speed * dt

        if dx != 0 or dy != 0:
            self.camera.pan(dx, dy)
