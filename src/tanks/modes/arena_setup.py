"""Arena setup and initialization."""

from typing import TYPE_CHECKING

from tanks.bots import BotController
from tanks.bots.simple_bot import SimpleBot
from tanks.bots.smart_bot import SmartBot
from tanks.modes.arena import ArenaConfig, ArenaSize
from tanks.perception import TerrainMemory, VisionSystem
from tanks.physics import CollisionSystem

if TYPE_CHECKING:
    from tanks.core.game import Game
    from tanks.input.controller import Controller
    from tanks.entities.tank import Tank


class ArenaSetup:
    """Handles arena initialization and bot spawning."""

    @staticmethod
    def setup_arena(game: "Game", config: ArenaConfig) -> None:
        """Set up an arena battle with multiple bots.

        Spawns procedurally generated map and creates bot controllers for each tank.

        Args:
            game: The game instance.
            config: Arena configuration.

        """
        # Generate map with configured terrain
        from tanks.maps import GeneratorConfig, MapGenerator

        # Map MapSize enum to width/height
        map_size_dims = {
            "SMALL": (20, 11),
            "MEDIUM": (40, 22),
            "LARGE": (60, 34),
            "HUGE": (80, 45),
        }
        width, height = map_size_dims.get(config.map_size.name, (40, 22))

        generator_config = GeneratorConfig(
            width=width,
            height=height,
            pattern=config.terrain_pattern,
            num_spawn_points=config.arena_size.tank_count,
            seed=config.seed,
        )
        generator = MapGenerator(generator_config)
        game.state.game_map = generator.generate()

        # Initialize physics and perception systems
        game.collision_system = CollisionSystem(game.state.game_map)
        game.vision_system = VisionSystem(game.state.game_map)

        # Set camera bounds
        game.camera.set_map_bounds(game.state.game_map)

        # Spawn tanks and assign bot controllers
        for i, bot_type in enumerate(config.bot_types):
            tank = game.spawn_tank(spawn_index=i)
            if tank:
                # Initialize fog memory for the tank
                tank.fog_memory = TerrainMemory(
                    game.state.game_map.width,
                    game.state.game_map.height,
                )
                controller = _create_bot_controller(bot_type, tank, game)
                game.add_input_handler(controller)

    @staticmethod
    def setup_arena_from_size(game: "Game", arena_size: ArenaSize) -> ArenaConfig:
        """Create a standard arena config from size, then set it up.

        Args:
            game: The game instance.
            arena_size: Desired arena size (SKIRMISH, STANDARD, LARGE, CHAOS).

        Returns:
            The created ArenaConfig.

        """
        from tanks.maps import MapSize, TerrainPattern

        # Map arena size to map size
        map_size_map = {
            "SKIRMISH": MapSize.SMALL,
            "STANDARD": MapSize.MEDIUM,
            "LARGE": MapSize.LARGE,
            "CHAOS": MapSize.HUGE,
        }

        config = ArenaConfig(
            name=f"Arena - {arena_size.label}",
            arena_size=arena_size,
            map_size=map_size_map.get(arena_size.name, MapSize.MEDIUM),
            terrain_pattern=TerrainPattern.SCATTERED,
            bot_types=["simple", "smart", "smart"]
            if arena_size.tank_count >= 3
            else ["simple", "smart"],
        )

        config.bot_types = config.bot_types[: arena_size.tank_count]

        ArenaSetup.setup_arena(game, config)
        return config


def _create_bot_controller(bot_type: str, tank: "Tank", game: "Game") -> "Controller":
    """Create a bot controller of the specified type.

    Args:
        bot_type: Type of bot ("simple", "smart", "cpp").
        tank: Tank to control.
        game: Game instance (needed for bot updates).

    Returns:
        Configured controller.

    Raises:
        ValueError: If bot_type is unknown.

    """
    if bot_type == "simple":
        return BotController(tank, game, SimpleBot())
    elif bot_type == "smart":
        return BotController(tank, game, SmartBot())
    elif bot_type == "cpp":
        # Would require subprocess management
        raise NotImplementedError("C++ bots require separate runner")
    else:
        raise ValueError(f"Unknown bot type: {bot_type}")
