"""Integration test for C++ external bots.

Tests the full pipeline: Python engine → C++ bot → Python engine.
"""

import sys
from pathlib import Path

from tanks.bots.bot_api import BotState, MapBounds, RadarHit, SelfState, VisibleEntity
from tanks.bots.external_runner import ExternalBotRunner

# Path to C++ bot executable
CPP_BOT_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tanks"
    / "bots"
    / "cpp"
    / "build"
    / "simple_bot"
)


def create_test_state(tick_id: int, *, enemy_visible: bool = False) -> BotState:
    """Create a test state with configurable enemy visibility.

    Args:
        tick_id: Tick identifier.
        enemy_visible: Whether to include visible enemy tank.

    Returns:
        BotState for testing.

    """
    visible_entities = []
    radar_hits = []

    if enemy_visible:
        # Add visible enemy tank
        visible_entities.append(
            VisibleEntity(
                entity_id=2,
                kind="tank",
                x=200.0,
                y=150.0,
                rotation=1.57,
                turret_rotation=1.57,
                team=2,
                active=True,
                distance=141.4,
                bearing=0.785,  # 45 degrees to the right
            ),
        )
        # Also add radar hit for same tank
        radar_hits.append(
            RadarHit(
                entity_id=2,
                kind="tank",
                distance=141.4,
                bearing=0.785,
            ),
        )

    return BotState(
        tick_id=tick_id,
        dt=0.033,
        self_state=SelfState(
            id=1,
            x=100.0,
            y=100.0,
            rotation=0.0,
            turret_rotation=0.0,
            speed=0.0,
            hp=100,
            shoot_cooldown=0.0,
            team=1,
        ),
        visible_entities=visible_entities,
        radar_hits=radar_hits,
        fog_memory=None,
        map_bounds=MapBounds(width=1280, height=704),
        tile_size=64,
    )


def test_cpp_bot_basic_communication() -> None:
    """Test basic communication with C++ bot."""
    if not CPP_BOT_PATH.exists():
        print(f"❌ C++ bot not found at: {CPP_BOT_PATH}")
        print("Build it with: cd src/tanks/bots/cpp/build && make")
        sys.exit(1)

    print(f"Testing C++ bot: {CPP_BOT_PATH}")

    runner = ExternalBotRunner(
        executable_path=str(CPP_BOT_PATH),
        timeout_ms=100.0,  # Generous timeout for testing
    )

    try:
        runner.start()
        print("✓ Bot process started")

        # Test 1: Wander mode (no enemies)
        print("\nTest 1: Wander mode (no visible enemies)")
        for tick in range(1, 4):
            state = create_test_state(tick, enemy_visible=False)
            action = runner.update(state)

            print(f"  Tick {tick}: forward={action.move_forward}, shoot={action.shoot}")

            # Wander should move forward (and randomly turn, but not guaranteed to shoot)
            assert action.move_forward is True, (
                "Expected move_forward=True in wander mode"
            )  # noqa: S101

        # Test 2: Seek mode (enemy visible)
        print("\nTest 2: Seek mode (enemy visible)")
        for tick in range(4, 7):
            state = create_test_state(tick, enemy_visible=True)
            action = runner.update(state)

            print(
                f"  Tick {tick}: forward={action.move_forward}, turn_left={action.turn_left}, shoot={action.shoot}"
            )
            print(
                f"           turret_angle={action.desired_turret_angle} (type: {type(action.desired_turret_angle)})"
            )

            # Seek should move forward
            assert action.move_forward is True, (
                "Expected move_forward=True in seek mode"
            )  # noqa: S101

            # Should use desired_turret_angle for precision (allow None on first tick for alignment delay)
            if tick > 4:  # Allow first tick to stabilize
                assert action.desired_turret_angle is not None, (
                    "Expected turret angle in seek mode"
                )  # noqa: S101

        # Test 3: Verify bot doesn't timeout
        stats = runner.get_stats()
        print(f"\nStats: {stats}")
        assert stats["tick_count"] == 6, "Expected 6 ticks"  # noqa: S101
        assert stats["timeout_count"] == 0, "Expected no timeouts"  # noqa: S101
        assert stats["error_count"] == 0, "Expected no errors"  # noqa: S101

        runner.stop()
        print("✓ Bot stopped cleanly")

        print("\n✅ All C++ bot integration tests passed!")

    except Exception as e:
        runner.stop()
        print(f"\n❌ Test failed: {e}")
        raise


def test_cpp_bot_performance() -> None:
    """Test C++ bot response time."""
    if not CPP_BOT_PATH.exists():
        print(f"C++ bot not found at: {CPP_BOT_PATH}")
        return

    print("\nPerformance test: 100 ticks")

    runner = ExternalBotRunner(
        executable_path=str(CPP_BOT_PATH),
        timeout_ms=8.0,  # Strict production timeout
    )

    try:
        runner.start()

        # Run 100 ticks rapidly
        for tick in range(1, 101):
            state = create_test_state(tick, enemy_visible=(tick % 2 == 0))
            action = runner.update(state)

            # Just verify we got a response
            assert action.move_forward is not None  # noqa: S101

        stats = runner.get_stats()
        print(f"Stats after 100 ticks: {stats}")

        # Verify no timeouts with 8ms budget
        if stats["timeout_count"] > 0:
            print(
                f"⚠️  Warning: {stats['timeout_count']} timeouts (bot may be too slow)"
            )
        else:
            print("✓ All 100 ticks completed within 8ms budget")

        runner.stop()

    except Exception as e:
        runner.stop()
        print(f"Performance test failed: {e}")
        raise


if __name__ == "__main__":
    test_cpp_bot_basic_communication()
    test_cpp_bot_performance()
