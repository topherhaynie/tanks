"""Multi-agent training environment for NvM scenarios.

Extends TrainingEnvironment to support multiple opponents (1v2, 1v3, 2v2, etc).
Useful for survival training and team tactics.
"""

from typing import TYPE_CHECKING

import numpy as np

from tanks.bots import SimpleBot, SmartBot
from tanks.bots.bot_controller import BotController
from tanks.config.constants import INPUT_RATE, PHYSICS_RATE
from tanks.entities import Tank
from tanks.maps.generator import MapGenerator
from tanks.perception import TerrainMemory
from tanks.training.env import TrainingEnvironment
from tanks.training.rewards import RewardWeights, create_sparse_reward_calculator

if TYPE_CHECKING:
    from tanks.bots.bot_api import Bot
    from tanks.maps.generator import GeneratorConfig
    from tanks.rl.actions import ActionSpace
    from tanks.training.rewards import RewardCalculator


class MultiAgentEnvironment(TrainingEnvironment):
    """Training environment supporting NvM scenarios.

    Supports configurations like 1v2, 1v3, 2v2, etc. Agent always controls
    one tank (team 0), and multiple opponent bots can be spawned (team 1).

    Args:
        num_opponents: Number of opponent tanks. Default: 1.
        opponent_bots: List of bots to use. If None, uses SmartBot.
        map_generator_config: Map config for generation. Uses default if None.
        max_steps: Maximum steps per episode.
        action_space: Action space for agent.
        reward_calculator: Reward calculator. Uses survival-focused if None.

    """

    def __init__(
        self,
        num_opponents: int = 1,
        opponent_bots: list["Bot"] | None = None,
        map_generator_config: "GeneratorConfig | None" = None,
        max_steps: int = 3000,
        action_space: "ActionSpace | None" = None,
        reward_calculator: "RewardCalculator | None" = None,
    ) -> None:
        """Initialize multi-agent environment."""
        # Store multi-agent config
        self.num_opponents = num_opponents
        self.map_generator_config = map_generator_config

        # Default opponent bots
        if opponent_bots is None:
            # Mix of SimpleBot and SmartBot for variety
            opponent_bots = []
            for i in range(num_opponents):
                if i % 2 == 0:
                    opponent_bots.append(SmartBot())
                else:
                    opponent_bots.append(SimpleBot())
        # Use provided bots
        elif len(opponent_bots) < num_opponents:
            # Cycle if not enough bots provided
            while len(opponent_bots) < num_opponents:
                opponent_bots.append(SmartBot())

        self.opponent_bots = opponent_bots[:num_opponents]

        # If reward calculator not provided, use survival-focused one
        if reward_calculator is None:
            # For 1vN, emphasize survival and damage dealt
            weights = RewardWeights(
                kill=150.0,  # Bonus for kills when outnumbered
                death=-200.0,  # Heavy penalty for dying
                survival_per_second=0.5,  # Strong survival reward
                bullet_hit=15.0,  # Bonus for damage dealt
                bullet_hit_taken=-10.0,  # Higher penalty when outnumbered
                standing_still_penalty=-1.0,  # Encourage movement
                new_terrain_revealed=8.0,  # Strong exploration bonus
            )
            reward_calculator = create_sparse_reward_calculator()
            reward_calculator.weights = weights

        # Initialize parent (this will use default map, we'll replace it)
        super().__init__(
            map_config=None,  # We'll generate our own
            max_steps=max_steps,
            action_space=action_space,
            reward_calculator=reward_calculator,
            opponent_bot=None,  # We handle opponents ourselves
        )

        # Generate appropriate map
        if map_generator_config is not None:
            # Ensure enough spawn points
            map_generator_config.num_spawn_points = max(
                map_generator_config.num_spawn_points,
                num_opponents + 1,
            )
            generator = MapGenerator(map_generator_config)
            self.game_map = generator.generate()

        # Multiple opponent tanks
        self.opponent_tanks: list[Tank] = []
        self.opponent_controllers: list[BotController] = []

    def reset(self) -> np.ndarray:
        """Reset environment for new episode with multiple opponents.

        Returns:
            Initial observation (state vector).

        """
        # Clear entities
        self.tanks.clear()
        self.bullets.clear()
        self.missiles.clear()
        self.mines.clear()
        self.opponent_tanks.clear()
        self.opponent_controllers.clear()

        # Reset parent tracking
        from tanks.config.constants import INPUT_RATE, PHYSICS_RATE
        from tanks.core.clock import FixedClock
        from tanks.core.stats import StatsTracker

        self.physics_clock = FixedClock(PHYSICS_RATE)
        self.input_clock = FixedClock(INPUT_RATE)
        self.current_step = 0
        self.input_tick_id = 0
        self.reward_calculator.reset()
        self.state_encoder.reset()
        self.stats_tracker = StatsTracker()
        self.episode_count += 1

        # Regenerate map if using random generation
        if self.map_generator_config is not None:
            self.map_generator_config.num_spawn_points = max(
                self.map_generator_config.num_spawn_points,
                self.num_opponents + 1,
            )
            generator = MapGenerator(self.map_generator_config)
            self.game_map = generator.generate()

            # Update systems with new map
            from tanks.perception.vision import VisionSystem
            from tanks.physics.collision import CollisionSystem

            self.collision_system = CollisionSystem(self.game_map)
            self.vision_system = VisionSystem(self.game_map)

            # Update state encoder map bounds
            map_width, map_height = self.game_map.get_pixel_size()
            self.state_encoder.max_map_width = float(map_width)
            self.state_encoder.max_map_height = float(map_height)

        # Spawn agent tank (spawn point 0, team 0)
        spawn_data = self.game_map.get_spawn_point(0)
        if spawn_data:
            x, y, team = spawn_data
            self.agent_tank = Tank(x, y, 0)  # Always team 0
            self.agent_tank.fog_memory = TerrainMemory(
                self.game_map.width,
                self.game_map.height,
            )
            self.tanks.append(self.agent_tank)
            self.stats_tracker.register_tank(self.agent_tank)

        # Spawn multiple opponent tanks (team 1)
        for i in range(self.num_opponents):
            spawn_idx = i + 1
            spawn_data = self.game_map.get_spawn_point(spawn_idx)

            if spawn_data:
                x, y, _ = spawn_data
                opponent_tank = Tank(x, y, 1)  # Always team 1 (opponents)
                opponent_tank.fog_memory = TerrainMemory(
                    self.game_map.width,
                    self.game_map.height,
                )
                self.tanks.append(opponent_tank)
                self.stats_tracker.register_tank(opponent_tank)
                self.opponent_tanks.append(opponent_tank)

                # Create controller for this opponent
                bot = self.opponent_bots[i % len(self.opponent_bots)]
                controller = BotController(
                    opponent_tank,
                    self,  # Environment acts as game object
                    bot,
                )
                self.opponent_controllers.append(controller)

        # Get initial state
        return self._get_observation()

    def step(
        self,
        action: int,
    ) -> tuple[np.ndarray, float, bool, dict[str, float | bool | str]]:
        """Execute one step in the environment.

        Args:
            action: Action index to execute.

        Returns:
            Tuple of (next_state, reward, done, info).

        """
        # Check if agent tank is still alive
        if not self.agent_tank or not self.agent_tank.active:
            # Agent died
            done = True
            reward = self.reward_calculator.weights.death
            info = {
                "won": False,
                "survived": False,
                "opponents_killed": self._count_opponents_killed(),
                "survival_time": self.current_step / 30.0,  # Convert to seconds
            }
            return self._get_observation(), reward, done, info

        # Apply agent action
        bot_action = self.action_space.to_bot_action(action)
        self._apply_bot_action(self.agent_tank, bot_action)

        # Update opponent controllers on input tick
        for controller in self.opponent_controllers:
            if controller.tank.active:
                controller.update(1.0 / INPUT_RATE)
        self.input_tick_id += 1

        # Physics updates: fixed deterministic substeps per input step
        physics_per_input = PHYSICS_RATE // INPUT_RATE
        for _ in range(physics_per_input):
            self._update_physics(1.0 / PHYSICS_RATE)

        # Update perception systems
        self._update_perception()

        # Get next state
        next_state = self._get_observation()

        # Check termination conditions
        done = False
        info: dict[str, float | bool | str] = {"won": False, "survived": False}

        # Check if all opponents are dead (agent wins)
        opponents_alive = sum(1 for tank in self.opponent_tanks if tank.active)
        if opponents_alive == 0:
            done = True
            info["won"] = True
            info["survived"] = True
            info["agent_won"] = True
            info["agent_killed_opponent"] = True

        # Check if agent died (already handled above)
        if not self.agent_tank.active:
            done = True
            info["won"] = False
            info["survived"] = False
            info["agent_won"] = False
            info["agent_killed_opponent"] = False

        # Check max steps
        self.current_step += 1
        if self.current_step >= self.max_steps:
            done = True
            info["timeout"] = True
            # Bonus for surviving the full episode
            if self.agent_tank.active:
                info["survived"] = True

        # Add survival stats
        info["opponents_killed"] = self._count_opponents_killed()
        info["opponents_alive"] = opponents_alive
        info["survival_time"] = self.current_step / 30.0

        # Compute reward after info is finalized
        reward = self._compute_reward(info)

        return next_state, reward, done, info

    def _count_opponents_killed(self) -> int:
        """Count how many opponents have been killed."""
        return sum(1 for tank in self.opponent_tanks if not tank.active)

    def get_game_map(self):
        """Get game map for compatibility."""
        return self.game_map
