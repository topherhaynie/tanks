"""Headless training environment for reinforcement learning.

Provides a gymnasium-like interface for training RL agents without rendering overhead.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from tanks.bots.bot_controller import BotController
from tanks.bots.sensors import build_bot_state
from tanks.config.constants import INPUT_RATE, MISSILE_SPEED, PHYSICS_RATE
from tanks.core.clock import FixedClock
from tanks.core.events import EventSystem
from tanks.core.stats import StatsTracker
from tanks.entities import Bullet, Mine, Missile, Tank
from tanks.maps import MapLoader
from tanks.perception import RadarSystem, TerrainMemory, VisionSystem
from tanks.physics import CollisionSystem, MovementSystem, ProjectileSystem
from tanks.rl.actions import ActionSpace, DiscreteActionSpace
from tanks.rl.state import StateEncoder
from tanks.training.rewards import RewardCalculator, create_sparse_reward_calculator

if TYPE_CHECKING:
    from tanks.bots.bot_api import Bot


class TrainingEnvironment:
    """Headless game environment for RL training.

    Provides gymnasium-style interface without rendering overhead.
    Designed for maximum simulation speed (target: 10x real-time).
    """

    def __init__(
        self,
        map_config: dict | None = None,
        max_steps: int = 3000,
        action_space: ActionSpace | None = None,
        reward_calculator: RewardCalculator | None = None,
        opponent_bot: "Bot | None" = None,
    ) -> None:
        """Initialize training environment.

        Args:
            map_config: Map configuration (size, terrain). Uses default if None.
            max_steps: Maximum steps per episode (~100s at 30Hz).
            action_space: Action space for agent. Uses discrete if None.
            reward_calculator: Reward calculator. Uses sparse if None.
            opponent_bot: Optional opponent bot for training.

        """
        # Configuration
        self.max_steps = max_steps
        self.action_space = action_space or DiscreteActionSpace(auto_aim=True)
        self.reward_calculator = reward_calculator or create_sparse_reward_calculator()

        # Map setup
        if map_config is None:
            # Default: simple arena
            self.game_map = MapLoader.create_simple_arena(20, 11)
        elif "map" in map_config:
            # Explicit map object provided by generator
            self.game_map = map_config["map"]
        else:
            self.game_map = MapLoader.create_simple_arena(
                map_config.get("width", 20),
                map_config.get("height", 11),
            )

        # Core systems (no rendering)
        self.collision_system = CollisionSystem(self.game_map)
        self.movement_system = MovementSystem()
        self.projectile_system = ProjectileSystem()
        self.vision_system = VisionSystem(self.game_map)
        self.radar_system = RadarSystem()
        self.events = EventSystem()
        self.stats_tracker = StatsTracker()

        # Clocks (physics + input)
        self.physics_clock = FixedClock(PHYSICS_RATE)
        self.input_clock = FixedClock(INPUT_RATE)

        # Entity lists
        self.tanks: list[Tank] = []
        self.bullets: list[Bullet] = []
        self.missiles: list[Missile] = []
        self.mines: list[Mine] = []

        # Agent tank and opponent tank
        self.agent_tank: Tank | None = None
        self.opponent_tank: Tank | None = None
        self.opponent_bot = opponent_bot
        self.opponent_controller: BotController | None = None

        # State encoding
        self.state_encoder = StateEncoder(
            max_map_width=float(self.game_map.get_pixel_size()[0]),
            max_map_height=float(self.game_map.get_pixel_size()[1]),
        )

        # Episode tracking
        self.current_step = 0
        self.input_tick_id = 0
        self.episode_count = 0

    def set_game_map(self, game_map) -> None:
        """Set a new map and refresh dependent systems.

        Args:
            game_map: New map object to use.

        """
        self.game_map = game_map
        self.collision_system = CollisionSystem(self.game_map)
        self.vision_system = VisionSystem(self.game_map)

        map_width, map_height = self.game_map.get_pixel_size()
        self.state_encoder.max_map_width = float(map_width)
        self.state_encoder.max_map_height = float(map_height)

    def reset(self) -> np.ndarray:
        """Reset environment for new episode.

        Returns:
            Initial observation (state vector).

        """
        # Clear entities
        self.tanks.clear()
        self.bullets.clear()
        self.missiles.clear()
        self.mines.clear()

        # Reset clocks by re-creating them
        self.physics_clock = FixedClock(PHYSICS_RATE)
        self.input_clock = FixedClock(INPUT_RATE)

        # Reset tracking
        self.current_step = 0
        self.input_tick_id = 0
        self.reward_calculator.reset()
        self.state_encoder.reset()
        self.stats_tracker = StatsTracker()  # Fresh tracker
        self.episode_count += 1

        # Spawn agent tank (spawn point 0)
        spawn_data = self.game_map.get_spawn_point(0)
        if spawn_data:
            x, y, team = spawn_data
            self.agent_tank = Tank(x, y, team)
            self.agent_tank.fog_memory = TerrainMemory(
                self.game_map.width,
                self.game_map.height,
            )
            self.tanks.append(self.agent_tank)
            self.stats_tracker.register_tank(self.agent_tank)

        # Spawn opponent tank (spawn point 1)
        if self.opponent_bot:
            spawn_data = self.game_map.get_spawn_point(1)
            if spawn_data:
                x, y, team = spawn_data
                self.opponent_tank = Tank(x, y, 1 if team == 0 else 0)  # Opposite team
                self.opponent_tank.fog_memory = TerrainMemory(
                    self.game_map.width,
                    self.game_map.height,
                )
                self.tanks.append(self.opponent_tank)
                self.stats_tracker.register_tank(self.opponent_tank)

                # Create controller for opponent
                self.opponent_controller = BotController(
                    self.opponent_tank,
                    self,  # Pass environment as game
                    self.opponent_bot,
                )

        # Get initial observation
        return self._get_observation()

    def step(self, action: int | np.ndarray) -> tuple[np.ndarray, float, bool, dict]:
        """Execute one environment step.

        Args:
            action: Action from RL agent (int for discrete, array for continuous).

        Returns:
            Tuple of (observation, reward, done, info).

        """
        # Increment step
        self.current_step += 1

        # Convert action to bot action and apply to agent tank
        bot_action = self.action_space.to_bot_action(action)
        if self.agent_tank:
            self._apply_bot_action(self.agent_tank, bot_action)

        # Update opponent bot
        if self.opponent_controller and self.opponent_tank and self.opponent_tank.active:
            self.opponent_controller.update(1.0 / INPUT_RATE)

        # Step physics multiple times per input
        physics_per_input = PHYSICS_RATE // INPUT_RATE
        for _ in range(physics_per_input):
            self._update_physics(1.0 / PHYSICS_RATE)

        # Update perception systems
        self._update_perception()

        # Check termination conditions
        done = self._is_terminal()
        info = self._get_info()

        # Compute reward
        reward = self._compute_reward(info)

        # Get observation
        observation = self._get_observation()

        return observation, reward, done, info

    def _update_physics(self, dt: float) -> None:
        """Update physics simulation.

        Args:
            dt: Physics time step.

        """
        # Update tanks
        for tank in self.tanks:
            if tank.active:
                tank.update(dt)
                self.stats_tracker.update_survival_time(tank, dt)
                self.stats_tracker.update_distance(tank)

        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(dt)

            # Wall collision
            hit_wall, normal = self.collision_system.check_bullet_wall_collision(bullet)
            if hit_wall:
                if not self.projectile_system.bounce_bullet(
                    bullet,
                    normal[0],
                    normal[1],
                ):
                    bullet.destroy()

            # Tank collision
            if bullet.active:
                hit_tank = self.collision_system.check_bullet_tank_collision(
                    bullet,
                    self.tanks,
                )
                if hit_tank:
                    shooter = next(
                        (t for t in self.tanks if t.id == bullet.owner_id),
                        None,
                    )
                    if shooter:
                        self.stats_tracker.record_hit(shooter, hit_tank, bullet.damage)
                        # Notify reward calculator of hit
                        if shooter == self.agent_tank:
                            self.reward_calculator.record_hit("bullet")
                        self.state_encoder.record_hit()

                    was_destroyed = hit_tank.take_damage(bullet.damage)
                    if was_destroyed and shooter:
                        self.stats_tracker.record_kill(shooter, hit_tank)
                        if shooter == self.agent_tank:
                            self.state_encoder.record_kill()

                    bullet.destroy()

            # Remove inactive
            if not bullet.active:
                if bullet in self.bullets:
                    self.bullets.remove(bullet)

        # Update missiles
        for missile in self.missiles[:]:
            missile.update(dt)

            # Wall collision (no bounce)
            if self.collision_system.check_missile_wall_collision(missile):
                missile.destroy()

            # Tank collision
            if missile.active:
                hit_tank = self.collision_system.check_missile_tank_collision(
                    missile,
                    self.tanks,
                )
                if hit_tank:
                    shooter = next(
                        (t for t in self.tanks if t.id == missile.owner_id),
                        None,
                    )
                    if shooter:
                        self.stats_tracker.record_hit(shooter, hit_tank, missile.damage)
                        if shooter == self.agent_tank:
                            self.reward_calculator.record_hit("missile")
                        self.state_encoder.record_hit()

                    was_destroyed = hit_tank.take_damage(missile.damage)
                    if was_destroyed and shooter:
                        self.stats_tracker.record_kill(shooter, hit_tank)
                        if shooter == self.agent_tank:
                            self.state_encoder.record_kill()

                    missile.destroy()

            if not missile.active:
                if missile in self.missiles:
                    self.missiles.remove(missile)

        # Update mines
        for mine in self.mines[:]:
            mine.update(dt)

            # Check proximity to tanks
            hit_tank = self.collision_system.check_mine_proximity(mine, self.tanks)
            if hit_tank:
                mine.trigger()

            # Check collision with projectiles
            if mine.armed and mine.active:
                hit_projectile = self.collision_system.check_mine_collision_with_projectile(
                    mine,
                    self.bullets + self.missiles,
                )
                if hit_projectile:
                    mine.trigger()
                    hit_projectile.destroy()

            # Handle mine explosion
            if not mine.active:
                # Find owner tank for stats
                owner_tank = next(
                    (t for t in self.tanks if t.id == mine.owner_id),
                    None,
                )

                # Check if mine hit anyone (within blast radius)
                from tanks.config.constants import MINE_BLAST_RADIUS

                for tank in self.tanks:
                    if tank.id == mine.owner_id:
                        continue  # Don't damage owner

                    dx = tank.x - mine.x
                    dy = tank.y - mine.y
                    dist = (dx * dx + dy * dy) ** 0.5

                    if dist < MINE_BLAST_RADIUS:
                        if owner_tank:
                            self.stats_tracker.record_hit(
                                owner_tank,
                                tank,
                                mine.damage,
                            )
                            if owner_tank == self.agent_tank:
                                self.reward_calculator.record_hit("mine")
                                self.state_encoder.record_hit()

                        was_destroyed = tank.take_damage(mine.damage)
                        if was_destroyed and owner_tank:
                            self.stats_tracker.record_kill(owner_tank, tank)
                            if owner_tank == self.agent_tank:
                                self.state_encoder.record_kill()

                # Remove inactive mine
                if mine in self.mines:
                    self.mines.remove(mine)

        # Handle shooting from tanks
        for tank in self.tanks:
            if not tank.active:
                continue

            # Check if tank controller wants to shoot
            if hasattr(tank, "_wants_shoot") and tank._wants_shoot:
                tank._wants_shoot = False
                if tank.can_shoot():
                    tank.shoot()  # Set cooldown
                    # Create bullet
                    tip_x, tip_y = tank.get_turret_tip_position()
                    angle_rad = math.radians(tank.turret_angle)
                    vx = math.cos(angle_rad) * 400
                    vy = math.sin(angle_rad) * 400
                    bullet = Bullet(tip_x, tip_y, vx, vy, tank.id)
                    self.bullets.append(bullet)
                    # Track shot for reward
                    if tank == self.agent_tank:
                        self.state_encoder.record_shot_fired()
                        self.reward_calculator.record_shot(
                            enemy_visible=self._has_visible_enemy(tank),
                        )

            # Check missile
            if hasattr(tank, "_wants_missile") and tank._wants_missile:
                tank._wants_missile = False
                if tank.can_fire_missile():
                    tank.fire_missile()  # Set cooldown
                    # Create missile
                    tip_x, tip_y = tank.get_turret_tip_position()
                    angle_rad = math.radians(tank.turret_angle)
                    vx = math.cos(angle_rad) * MISSILE_SPEED
                    vy = math.sin(angle_rad) * MISSILE_SPEED
                    missile = Missile(tip_x, tip_y, vx, vy, tank.id)
                    self.missiles.append(missile)
                    if tank == self.agent_tank:
                        self.state_encoder.record_shot_fired()
                        self.reward_calculator.record_shot(
                            enemy_visible=self._has_visible_enemy(tank),
                        )

            # Check mine
            if hasattr(tank, "_wants_mine") and tank._wants_mine:
                tank._wants_mine = False
                if tank.can_place_mine():
                    tank.place_mine()  # Set cooldown and decrement count
                    # Create mine
                    mine = Mine(tank.x, tank.y, tank.id)
                    self.mines.append(mine)

        # Apply movement
        for tank in self.tanks:
            if tank.active:
                self.movement_system.update_tank_movement(
                    tank,
                    getattr(tank, "move_forward", False),
                    getattr(tank, "move_backward", False),
                    getattr(tank, "turn_left", False),
                    getattr(tank, "turn_right", False),
                    dt,
                )
                # TODO: Add proper collision resolution if needed
                # For now, tanks can overlap (simplified training)

    def _update_perception(self) -> None:
        """Update perception systems for all tanks."""
        for tank in self.tanks:
            if not tank.active:
                continue

            # Update vision
            all_entities = [*self.tanks, *self.bullets, *self.missiles, *self.mines]
            self.vision_system.update_vision(tank, all_entities)

            # Update radar (not blocked by walls)
            tank.radar_detections = self.radar_system.detect_entities(
                tank,
                self.tanks + self.mines,
            )

    def _apply_bot_action(self, tank: Tank, action) -> None:
        """Apply bot action to tank.

        Args:
            tank: Tank to control.
            action: BotAction from agent.

        """
        # Set movement flags
        tank.move_forward = action.move_forward
        tank.move_backward = action.move_backward
        tank.turn_left = action.turn_left
        tank.turn_right = action.turn_right
        tank.turret_left = action.turret_left
        tank.turret_right = action.turret_right

        # Store shooting desires (will be processed in physics update)
        tank._wants_shoot = action.shoot
        tank._wants_missile = action.fire_missile
        tank._wants_mine = action.place_mine

        # Auto-aim turret if enabled
        if getattr(self.action_space, "auto_aim", False):
            self._auto_aim_turret(tank)

    def _auto_aim_turret(self, tank: Tank) -> None:
        """Auto-aim turret at nearest enemy.

        Args:
            tank: Tank to aim.

        """
        enemies = [e for e in tank.visible_entities if hasattr(e, "team") and e.team != tank.team and e.active]

        if enemies:
            nearest = min(enemies, key=lambda e: math.hypot(e.x - tank.x, e.y - tank.y))
            # Calculate angle to enemy
            dx = nearest.x - tank.x
            dy = nearest.y - tank.y
            target_angle = math.degrees(math.atan2(dy, dx))

            # Set turret to aim at enemy
            tank.turret_angle = target_angle

    def _has_visible_enemy(self, tank: Tank) -> bool:
        """Check if the tank currently sees at least one active enemy tank.

        Args:
            tank: Tank to evaluate visibility for.

        Returns:
            True when at least one enemy tank is visible.

        """
        return any(
            hasattr(entity, "team") and entity.team != tank.team and entity.active for entity in tank.visible_entities
        )

    def _get_observation(self) -> np.ndarray:
        """Get current observation (state vector).

        Returns:
            Numpy array with encoded state.

        """
        if not self.agent_tank or not self.agent_tank.active:
            return np.zeros(self.state_encoder.TOTAL_DIM, dtype=np.float32)

        # Build bot state from sensors
        bot_state = build_bot_state(
            self.agent_tank,
            self,  # Pass environment as "game" for sensor access
            self.input_tick_id,
            1.0 / INPUT_RATE,
        )

        # Encode to vector
        return self.state_encoder.encode(bot_state)

    def _compute_reward(self, info: dict) -> float:
        """Compute reward for current step.

        Args:
            info: Environment info dict.

        Returns:
            Reward value.

        """
        if not self.agent_tank:
            return 0.0

        # Build bot state for reward calculation
        bot_state = build_bot_state(
            self.agent_tank,
            self,
            self.input_tick_id,
            1.0 / INPUT_RATE,
        )

        # Compute reward
        reward = self.reward_calculator.compute_step_reward(
            bot_state,
            is_dead=not self.agent_tank.active,
            did_kill=info.get("agent_killed_opponent", False),
            did_win=info.get("agent_won", False),
        )

        return reward

    def _is_terminal(self) -> bool:
        """Check if episode is done.

        Returns:
            True if episode ended.

        """
        # Agent died
        if not self.agent_tank or not self.agent_tank.active:
            return True

        # Opponent died (victory)
        if self.opponent_tank and not self.opponent_tank.active:
            return True

        # Max steps reached
        if self.current_step >= self.max_steps:
            return True

        return False

    def _get_info(self) -> dict:
        """Get environment info dict.

        Returns:
            Dictionary with episode information.

        """
        info: dict = {
            "step": self.current_step,
            "agent_alive": self.agent_tank.active if self.agent_tank else False,
            "opponent_alive": self.opponent_tank.active if self.opponent_tank else False,
            "agent_hp": self.agent_tank.hp if self.agent_tank else 0,
            "opponent_hp": self.opponent_tank.hp if self.opponent_tank else 0,
        }

        # Check victory/defeat conditions
        if self.agent_tank and self.opponent_tank:
            info["agent_won"] = not self.opponent_tank.active and self.agent_tank.active
            info["agent_killed_opponent"] = not self.opponent_tank.active and self.agent_tank.active

        return info

    def close(self) -> None:
        """Clean up environment resources."""
        self.tanks.clear()
        self.bullets.clear()
        self.missiles.clear()
        self.mines.clear()

    # Duck-type as Game for sensor compatibility
    @property
    def state(self):
        """Provide game state interface for sensors."""

        class StateWrapper:
            """Wrapper to provide state interface."""

            def __init__(self, env: "TrainingEnvironment") -> None:
                self.game_map = env.game_map

        return StateWrapper(self)
