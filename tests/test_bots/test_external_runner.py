"""Test script for external bot runner.

Tests the external bot subprocess management and JSON IPC.
This creates a mock external bot as a Python script that simulates
a C++ bot's stdin/stdout behavior.
"""

import sys
import tempfile
from pathlib import Path

from tanks.bots.bot_api import BotState, MapBounds, SelfState
from tanks.bots.external_runner import ExternalBotRunner


def create_mock_bot_script() -> Path:
    """Create a mock external bot script for testing.

    Returns:
        Path to executable mock bot script.

    """
    script_content = '''#!/usr/bin/env python3
"""Mock external bot for testing."""
import json
import sys

while True:
    try:
        # Read state from stdin
        line = sys.stdin.readline()
        if not line:
            break
            
        state = json.loads(line)
        
        # Simple response: move forward and shoot
        action = {
            "type": "action",
            "tick_id": state["tick_id"],
            "move_forward": True,
            "move_backward": False,
            "turn_left": False,
            "turn_right": False,
            "turret_left": False,
            "turret_right": False,
            "shoot": True,
            "desired_turret_angle": None
        }
        
        # Write action to stdout
        print(json.dumps(action), flush=True)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        break
'''

    # Create temporary executable script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = Path(f.name)

    script_path.chmod(0o755)  # Make executable
    return script_path


def create_test_state(tick_id: int) -> BotState:
    """Create a minimal test state.

    Args:
        tick_id: Tick identifier.

    Returns:
        BotState for testing.

    """
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
        visible_entities=[],
        radar_hits=[],
        fog_memory=None,
        map_bounds=MapBounds(width=1280, height=704),
        tile_size=64,
    )


def test_external_runner():
    """Test external bot runner with mock bot."""
    print("Creating mock external bot...")
    bot_script = create_mock_bot_script()

    try:
        # Create runner with python3 interpreter
        print(f"Starting bot: {bot_script}")
        runner = ExternalBotRunner(
            executable_path=sys.executable,  # Use current Python interpreter
            timeout_ms=100.0,  # Generous timeout for testing
            args=[str(bot_script)],
        )

        runner.start()
        print("Bot started successfully")

        # Test a few ticks
        for tick in range(1, 6):
            print(f"\nTick {tick}:")
            state = create_test_state(tick)
            action = runner.update(state)

            print(f"  State sent: tick_id={state.tick_id}")
            print(
                f"  Action received: move_forward={action.move_forward}, shoot={action.shoot}"
            )

            assert action.move_forward is True, "Expected move_forward=True"  # noqa: S101
            assert action.shoot is True, "Expected shoot=True"  # noqa: S101

        # Check stats
        stats = runner.get_stats()
        print(f"\nStats: {stats}")
        assert stats["tick_count"] == 5, "Expected 5 ticks"  # noqa: S101
        assert stats["timeout_count"] == 0, "Expected no timeouts"  # noqa: S101
        assert stats["error_count"] == 0, "Expected no errors"  # noqa: S101

        # Stop runner
        runner.stop()
        print("\nBot stopped successfully")

        print("\n✅ All tests passed!")

    finally:
        # Cleanup
        bot_script.unlink()


if __name__ == "__main__":
    test_external_runner()
