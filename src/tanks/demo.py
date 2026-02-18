"""Demo mode with two-player gameplay."""

from tanks.core import Game
from tanks.input import KeyboardController
from tanks.input.keyboard import KeyboardController2


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
        controller1 = KeyboardController(player1_tank, game)
        game.add_input_handler(controller1)
        # Set fog of war perspective to player 1
        game.renderer.set_perspective_tank(player1_tank)

    # Spawn player 2 tank
    player2_tank = game.spawn_tank(1)
    if player2_tank:
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


if __name__ == "__main__":
    run_demo()
