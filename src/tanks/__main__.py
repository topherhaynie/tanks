"""The main entry point for the tanks game."""

from tanks.core import Game
from tanks.input import KeyboardController


def main() -> None:
    """Run the tank battle game."""
    # Create game
    game = Game()

    # Load map
    game.load_map()  # Uses default simple arena

    # Spawn player tank
    player_tank = game.spawn_tank(0)

    # Add keyboard controller
    if player_tank:
        controller = KeyboardController(player_tank, game)
        game.add_input_handler(controller)

    # Run game
    print("Tank Battle - Phase 1")  # noqa: T201
    print("Controls: WASD to move, Mouse to aim, Space to shoot")  # noqa: T201
    print("Press ESC to quit, F1 to toggle debug, P to pause")  # noqa: T201

    game.run()


if __name__ == "__main__":
    main()
