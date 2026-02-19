"""Demo modes for local play."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tanks.bots import (
    BotController,
    ExternalBotController,
    ExternalBotRunner,
    SimpleBot,
    SmartBot,
)
from tanks.config.constants import TILE_SIZE
from tanks.core import Game
from tanks.input import KeyboardController
from tanks.input.keyboard import KeyboardController2
from tanks.rendering.camera import CameraMode

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


def run_demo() -> bool:
    """Run the two-player demo mode.

    Player 1 uses WASD + Mouse + Space.
    Player 2 uses Arrow keys + JL + RCtrl.

    Returns:
        True if user wants to quit the application, False to return to menu.

    """
    # Create game
    game = Game()

    # Load map
    game.load_map()  # Uses default simple arena

    # Spawn player 1 tank
    player1_tank = game.spawn_tank(0)
    if player1_tank:
        _position_tank(player1_tank, game, 0.1, 0.1)
        controller1 = KeyboardController(player1_tank, game)
        game.add_input_handler(controller1)
        # Set fog of war perspective to player 1
        game.renderer.set_perspective_tank(player1_tank)

    # Spawn player 2 tank
    player2_tank = game.spawn_tank(1)
    if player2_tank:
        _position_tank(player2_tank, game, 0.9, 0.9)
        controller2 = KeyboardController2(player2_tank, game)
        game.add_input_handler(controller2)

    # Run game
    print("Tank Battle - Two Player Demo")  # noqa: T201
    print("Player 1: WASD to move, Mouse to aim, Space to shoot")  # noqa: T201
    print("Player 2: Arrow keys to move, JL to aim turret, RCtrl to shoot")  # noqa: T201
    print(
        "F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, F6=stats, P=pause",
    )
    print("C=cycle camera, Tab=switch follow target, +/-=zoom")  # noqa: T201
    print()  # noqa: T201

    # Set camera to follow player 1
    game.camera.set_mode(CameraMode.FOLLOW)
    if player1_tank:
        game.camera.set_follow_target(player1_tank)

    game.run()

    # Return whether user wants to quit the app
    return game.state.quit_app


def run_bot_demo() -> bool:
    """Run the player vs bot demo mode.

    Player uses WASD + Mouse + Space. Bot uses the simple bot controller.

    Returns:
        True if user wants to quit the application, False to return to menu.

    """
    game = Game()
    game.load_map()

    player_tank = game.spawn_tank(0)
    if player_tank:
        _position_tank(player_tank, game, 0.1, 0.1)
        controller = KeyboardController(player_tank, game)
        game.add_input_handler(controller)
        game.renderer.set_perspective_tank(player_tank)

    bot_tank = game.spawn_tank(1)
    if bot_tank:
        _position_tank(bot_tank, game, 0.9, 0.9)
        bot_controller = BotController(bot_tank, game, SimpleBot())
        game.add_input_handler(bot_controller)

    print("Tank Battle - Player vs Bot")  # noqa: T201
    print("Player: WASD to move, Mouse to aim, Space to shoot")  # noqa: T201
    print("Bot: Simple seek/wander behavior")  # noqa: T201
    print(
        "F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, F6=stats, P=pause",
    )
    print("C=cycle camera, Tab=switch follow target, +/-=zoom")  # noqa: T201
    print()  # noqa: T201

    # Set camera to follow player
    game.camera.set_mode(CameraMode.FOLLOW)
    if player_tank:
        game.camera.set_follow_target(player_tank)

    game.run()

    return game.state.quit_app


def run_bot_battle_demo() -> bool:
    """Run the bot vs bot demo mode with global visibility.

    Returns:
        True if user wants to quit the application, False to return to menu.

    """
    game = Game()
    game.load_map()

    bot1_tank = game.spawn_tank(0)
    if bot1_tank:
        _position_tank(bot1_tank, game, 0.1, 0.1)
        bot1_controller = BotController(bot1_tank, game, SimpleBot())
        game.add_input_handler(bot1_controller)

    bot2_tank = game.spawn_tank(1)
    if bot2_tank:
        _position_tank(bot2_tank, game, 0.9, 0.9)
        bot2_controller = BotController(bot2_tank, game, SmartBot())
        game.add_input_handler(bot2_controller)

    game.renderer.set_perspective_tank(None)
    game.renderer.set_observer_view(
        [tank for tank in [bot1_tank, bot2_tank] if tank],
        fog_opacity=0.5,
        fog_colors=((70, 110, 255), (255, 90, 90)),
        hidden_alpha=0.7,
    )

    print("Tank Battle - Bot vs Bot (Global View)")  # noqa: T201
    print("Bot 1: Simple seek/wander")  # noqa: T201
    print("Bot 2: Smart seek/radar pursuit")  # noqa: T201
    print(
        "F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, F6=stats, P=pause",
    )
    print("C=cycle camera, Tab=switch follow target, +/-=zoom")  # noqa: T201
    print()  # noqa: T201

    # Set camera to global view (shows entire map)
    game.camera.set_mode(CameraMode.GLOBAL)

    game.run()

    # Show final statistics
    game.display_final_stats()

    return game.state.quit_app


def run_mixed_bot_battle_demo() -> bool:
    """Run a 3-way bot battle: C++ bot vs Python SimpleBot vs Python SmartBot.

    Demonstrates external C++ bot competing with internal Python bots.
    Uses global observer view to watch all three bots.

    Returns:
        True if user wants to quit the application, False to return to menu.

    """
    # Find C++ bot executable
    cpp_bot_path = Path(__file__).parent / "bots" / "cpp" / "build" / "simple_bot"

    if not cpp_bot_path.exists():
        print("❌ C++ bot not found!")  # noqa: T201
        print(f"Expected at: {cpp_bot_path}")  # noqa: T201
        print(
            "Build it with: cd src/tanks/bots/cpp && mkdir -p build && cd build && cmake .. && make",
        )
        print("\nPress Enter to return to menu...")  # noqa: T201
        input()
        return False

    game = Game()
    game.load_map()

    # Track runner for cleanup
    runner = None

    # Spawn Bot 1: C++ External Bot (Team 0)
    cpp_bot_tank = game.spawn_tank(0)
    if cpp_bot_tank:
        _position_tank(cpp_bot_tank, game, 0.25, 0.3)  # Left side
        try:
            runner = ExternalBotRunner(str(cpp_bot_path), timeout_ms=8.0)
            runner.start()
            cpp_controller = ExternalBotController(cpp_bot_tank, game, runner)
            game.add_input_handler(cpp_controller)
            print(f"✓ C++ bot started: {cpp_bot_path.name}")  # noqa: T201
        except Exception as e:
            print(f"❌ Failed to start C++ bot: {e}")  # noqa: T201
            print("Continuing without C++ bot...")  # noqa: T201

    # Spawn Bot 2: Python SimpleBot (Team 1)
    simple_bot_tank = game.spawn_tank(1)
    if simple_bot_tank:
        _position_tank(simple_bot_tank, game, 0.75, 0.3)  # Right side
        simple_controller = BotController(simple_bot_tank, game, SimpleBot())
        game.add_input_handler(simple_controller)

    # Spawn Bot 3: Python SmartBot (Team 2)
    smart_bot_tank = game.spawn_tank(2)
    if smart_bot_tank:
        _position_tank(smart_bot_tank, game, 0.5, 0.7)  # Bottom center
        smart_controller = BotController(smart_bot_tank, game, SmartBot())
        game.add_input_handler(smart_controller)

    # Set up observer view with three fog colors
    game.renderer.set_perspective_tank(None)
    active_tanks = [
        tank for tank in [cpp_bot_tank, simple_bot_tank, smart_bot_tank] if tank
    ]
    game.renderer.set_observer_view(
        active_tanks,
        fog_opacity=0.5,
        fog_colors=((70, 110, 255), (255, 90, 90), (90, 255, 90)),  # Blue, Red, Green
        hidden_alpha=0.7,
    )

    print("\nTank Battle - Mixed Bot Battle (3-Way)")  # noqa: T201
    print("Bot 1 (Blue):  C++ External Bot (seek/wander)")  # noqa: T201
    print("Bot 2 (Red):   Python SimpleBot (seek/wander)")  # noqa: T201
    print("Bot 3 (Green): Python SmartBot (radar pursuit)")  # noqa: T201
    print(
        "F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, F6=stats, P=pause",
    )
    print("C=cycle camera, Tab=switch follow target, +/-=zoom")  # noqa: T201
    print()  # noqa: T201

    # Set camera to global view (shows entire map)
    game.camera.set_mode(CameraMode.GLOBAL)

    game.run()

    # Clean up external bot process
    if runner is not None:
        try:
            runner.stop()
            print("✓ C++ bot stopped")  # noqa: T201
        except Exception as e:
            print(f"Warning: Error stopping C++ bot: {e}", file=sys.stderr)

    # Show final statistics
    game.display_final_stats()

    return game.state.quit_app


def run_arena_demo() -> bool:
    """Run an arena battle with 4+ bots on a procedurally generated map.

    Demonstrates multi-tank battles with configurable difficulty levels.
    Uses global observer view to watch all bots compete.

    Returns:
        True if user wants to quit the application, False to return to menu.

    """
    from tanks.modes import ArenaSize
    from tanks.modes.arena_setup import ArenaSetup

    print("\n=== ARENA BATTLE ===")  # noqa: T201
    print("1. Skirmish (3-4 tanks, small map)")  # noqa: T201
    print("2. Standard (4 tanks, medium map)")  # noqa: T201
    print("3. Large (6 tanks, large map)")  # noqa: T201
    print("4. Chaos (8 tanks, huge map)")  # noqa: T201
    print("q. Cancel")  # noqa: T201

    choice = input("Select arena size: ").strip().lower()

    arena_sizes = {
        "1": ArenaSize.SKIRMISH,
        "2": ArenaSize.STANDARD,
        "3": ArenaSize.LARGE,
        "4": ArenaSize.CHAOS,
    }

    if choice not in arena_sizes:
        return False

    game = Game()

    # Set up arena with selected size
    ArenaSetup.setup_arena_from_size(game, arena_sizes[choice])

    # Set up observer view with distinct fog colors
    observer_tanks = game.state.tanks
    fog_colors = (
        (70, 110, 255),  # Blue
        (255, 90, 90),  # Red
        (90, 255, 90),  # Green
        (255, 200, 50),  # Orange
        (200, 90, 255),  # Purple
        (90, 255, 255),  # Cyan
        (255, 150, 150),  # Pink
        (150, 200, 100),  # Olive
    )
    game.renderer.set_perspective_tank(None)
    game.renderer.set_observer_view(
        observer_tanks,
        fog_opacity=0.5,
        fog_colors=fog_colors[: len(observer_tanks)],
        hidden_alpha=0.7,
    )

    print(f"\nArena Battle - {arena_sizes[choice].label}")  # noqa: T201
    for i, tank in enumerate(observer_tanks):
        print(f"Tank {i + 1}: {tank.team} (bot)")  # noqa: T201
    print(
        "F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, F6=stats, P=pause",
    )
    print("C=cycle camera, Tab=switch follow target, +/-=zoom")  # noqa: T201
    print()  # noqa: T201

    # Set camera to global view (shows entire map)
    game.camera.set_mode(CameraMode.GLOBAL)

    game.run()

    # Show final statistics
    game.display_final_stats()

    return game.state.quit_app


def _position_tank(tank: "Tank", game: Game, x_ratio: float, y_ratio: float) -> None:
    """Place a tank using map-relative coordinates.

    Args:
        tank: Tank to reposition.
        game: Game instance with loaded map.
        x_ratio: Horizontal ratio in [0, 1].
        y_ratio: Vertical ratio in [0, 1].

    """
    if not game.state.game_map:
        return

    map_width_px, map_height_px = game.state.game_map.get_pixel_size()
    margin = TILE_SIZE * 2
    x = margin + (map_width_px - margin * 2) * x_ratio
    y = margin + (map_height_px - margin * 2) * y_ratio

    tank.x = x
    tank.y = y


if __name__ == "__main__":
    run_demo()
