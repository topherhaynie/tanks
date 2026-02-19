"""Demo modes for local play."""

from typing import TYPE_CHECKING

from tanks.bots import BotController, SimpleBot, SmartBot
from tanks.config.constants import TILE_SIZE
from tanks.core import Game
from tanks.input import KeyboardController
from tanks.input.keyboard import KeyboardController2

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
    print("F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, P=pause")  # noqa: T201
    print()  # noqa: T201

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
    print("F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, P=pause")  # noqa: T201
    print()  # noqa: T201

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
    print("F1=debug all, F2=hitboxes, F3=vision ranges, F4=radar blips, P=pause")  # noqa: T201
    print()  # noqa: T201

    game.run()

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
