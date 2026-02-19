"""The main entry point for the tanks game."""

import pygame

from tanks.demo import (
    run_arena_demo,
    run_bot_battle_demo,
    run_bot_demo,
    run_demo,
    run_mixed_bot_battle_demo,
)


def print_menu() -> None:
    """Print the game mode selection menu."""
    print("=" * 50)  # noqa: T201
    print("TANK BATTLE - Phase 4")  # noqa: T201
    print("=" * 50)  # noqa: T201
    print()  # noqa: T201
    print("Select Game Mode:")  # noqa: T201
    print("  1. Two-Player Demo")  # noqa: T201
    print("  2. Player vs Bot")  # noqa: T201
    print("  3. Bot vs Bot (Global View)")  # noqa: T201
    print("  4. Mixed Bot Battle (C++ + Python)")  # noqa: T201
    print("  5. Arena Battle (4-8 bots) 🆕")  # noqa: T201
    print("  q. Quit")  # noqa: T201
    print()  # noqa: T201


def main() -> None:
    """Run the tank battle game with mode selection."""
    try:
        while True:
            print_menu()
            choice = input("Enter your choice: ").strip().lower()
            print()  # noqa: T201

            if choice == "1":
                should_quit = run_demo()
                if should_quit:
                    print("\nThanks for playing!")  # noqa: T201
                    break
                print("\nReturning to menu...\n")  # noqa: T201
            elif choice == "2":
                should_quit = run_bot_demo()
                if should_quit:
                    print("\nThanks for playing!")  # noqa: T201
                    break
                print("\nReturning to menu...\n")  # noqa: T201
            elif choice == "3":
                should_quit = run_bot_battle_demo()
                if should_quit:
                    print("\nThanks for playing!")  # noqa: T201
                    break
                print("\nReturning to menu...\n")  # noqa: T201
            elif choice == "4":
                should_quit = run_mixed_bot_battle_demo()
                if should_quit:
                    print("\nThanks for playing!")  # noqa: T201
                    break
                print("\nReturning to menu...\n")  # noqa: T201
            elif choice == "5":
                should_quit = run_arena_demo()
                if should_quit:
                    print("\nThanks for playing!")  # noqa: T201
                    break
                print("\nReturning to menu...\n")  # noqa: T201
            elif choice == "q":
                print("Thanks for playing!")  # noqa: T201
                break
            else:
                print(f"Invalid choice: '{choice}'. Please try again.\n")  # noqa: T201
    finally:
        # Clean up pygame on exit
        pygame.quit()


if __name__ == "__main__":
    main()
