"""External bot runner with subprocess management and JSON IPC."""

import json
import subprocess
import time
from dataclasses import asdict
from typing import TYPE_CHECKING

from tanks.bots.bot_api import BotAction, BotState

if TYPE_CHECKING:
    from collections.abc import Sequence


class ExternalBotError(Exception):
    """Base exception for external bot errors."""


class BotTimeoutError(ExternalBotError):
    """Bot exceeded time budget for response."""


class BotCrashError(ExternalBotError):
    """Bot process crashed or exited unexpectedly."""


class BotProtocolError(ExternalBotError):
    """Bot violated communication protocol."""


class ExternalBotRunner:
    """Manages external bot process via JSON stdin/stdout communication.

    Handles subprocess lifecycle, JSON serialization, timeout enforcement,
    and error recovery for external bots (e.g., C++, Rust, etc.).

    Attributes:
        executable_path: Path to bot executable.
        timeout_ms: Per-tick timeout budget in milliseconds.
        process: Subprocess handle (None if not running).
        last_action: Most recent action for fallback on timeout.

    """

    def __init__(
        self,
        executable_path: str,
        timeout_ms: float = 8.0,
        args: "Sequence[str] | None" = None,
    ) -> None:
        """Initialize external bot runner.

        Args:
            executable_path: Path to bot executable.
            timeout_ms: Timeout budget per tick in milliseconds (default 8ms).
            args: Additional command-line arguments for bot process.

        """
        self.executable_path = executable_path
        self.timeout_ms = timeout_ms
        self.args = list(args) if args else []
        self.process: subprocess.Popen[bytes] | None = None
        self.last_action = BotAction()  # Default no-op action
        self._tick_count = 0
        self._timeout_count = 0
        self._error_count = 0

    def start(self) -> None:
        """Start the external bot process.

        Raises:
            BotCrashError: If process fails to start.

        """
        if self.process is not None:
            return  # Already running

        try:
            self.process = subprocess.Popen(  # noqa: S603
                [self.executable_path, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered for low latency
            )
        except (OSError, subprocess.SubprocessError) as e:
            msg = f"Failed to start bot process: {e}"
            raise BotCrashError(msg) from e

    def stop(self) -> None:
        """Stop the external bot process gracefully."""
        if self.process is None:
            return

        try:
            self.process.terminate()
            self.process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        finally:
            self.process = None

    def restart(self) -> None:
        """Restart the bot process (recovery from error)."""
        self.stop()
        time.sleep(0.1)  # Brief cooldown
        self.start()

    def update(self, state: BotState) -> BotAction:
        """Send state to bot and receive action response.

        Args:
            state: Current bot state snapshot.

        Returns:
            BotAction from bot (or last valid action on timeout/error).

        Raises:
            BotCrashError: If bot process is not running.

        """
        if self.process is None:
            msg = "Bot process not running"
            raise BotCrashError(msg)

        self._tick_count += 1

        try:
            action = self._exchange_state_action(state)
        except BotTimeoutError:
            self._timeout_count += 1
            return self.last_action  # Fallback to last action
        except (BotProtocolError, BotCrashError):
            self._error_count += 1
            if self._error_count >= 3:  # noqa: PLR2004
                raise  # Give up after 3 consecutive errors
            return self.last_action  # Fallback to last action
        else:
            self.last_action = action
            return action

    def _exchange_state_action(self, state: BotState) -> BotAction:
        """Send state and receive action with timeout enforcement.

        Args:
            state: Bot state to send.

        Returns:
            BotAction from bot.

        Raises:
            BotTimeoutError: If bot exceeds timeout budget.
            BotProtocolError: If bot sends invalid JSON or mismatched tick_id.
            BotCrashError: If bot process died.

        """
        if (
            self.process is None
            or self.process.stdin is None
            or self.process.stdout is None
        ):
            msg = "Bot process not properly initialized"
            raise BotCrashError(msg)

        # Check if process is alive
        if self.process.poll() is not None:
            msg = f"Bot process exited with code {self.process.returncode}"
            raise BotCrashError(msg)

        # Serialize state to JSON
        state_dict = self._serialize_state(state)
        state_json = json.dumps(state_dict) + "\n"

        # Send state
        try:
            self.process.stdin.write(state_json.encode())
            self.process.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            msg = f"Failed to write to bot stdin: {e}"
            raise BotCrashError(msg) from e

        # Receive action with timeout
        start_time = time.perf_counter()
        timeout_sec = self.timeout_ms / 1000.0

        try:
            # Simple blocking read with timeout (not perfect but sufficient)
            line = self.process.stdout.readline()
            elapsed = time.perf_counter() - start_time

            if elapsed > timeout_sec:
                msg = f"Bot exceeded timeout: {elapsed * 1000:.2f}ms > {self.timeout_ms}ms"
                raise BotTimeoutError(msg)

            if not line:
                msg = "Bot closed stdout"
                raise BotCrashError(msg)

            action_dict = json.loads(line.decode())
            return self._deserialize_action(action_dict, state.tick_id)

        except json.JSONDecodeError as e:
            msg = f"Bot sent invalid JSON: {e}"
            raise BotProtocolError(msg) from e
        except (OSError, BrokenPipeError) as e:
            msg = f"Failed to read from bot stdout: {e}"
            raise BotCrashError(msg) from e

    def _serialize_state(self, state: BotState) -> dict:
        """Serialize BotState to JSON-compatible dict.

        Args:
            state: BotState to serialize.

        Returns:
            Dict representation matching external bot protocol.

        """
        state_dict = asdict(state)
        state_dict["type"] = "state"

        # Convert self_state and nested structures
        state_dict["self"] = state_dict.pop("self_state")

        # Fix field names for external protocol (entity_id → id)
        for entity in state_dict.get("visible_entities", []):
            if "entity_id" in entity:
                entity["id"] = entity.pop("entity_id")

        for hit in state_dict.get("radar_hits", []):
            if "entity_id" in hit:
                hit["id"] = hit.pop("entity_id")

        return state_dict

    def _deserialize_action(
        self,
        action_dict: dict,
        expected_tick_id: int,
    ) -> BotAction:
        """Deserialize action dict to BotAction.

        Args:
            action_dict: JSON dict from bot.
            expected_tick_id: Expected tick_id for validation.

        Returns:
            BotAction.

        Raises:
            BotProtocolError: If action_dict is invalid or tick_id mismatched.

        """
        if action_dict.get("type") != "action":
            msg = f"Expected type='action', got {action_dict.get('type')}"
            raise BotProtocolError(msg)

        tick_id = action_dict.get("tick_id")
        if tick_id != expected_tick_id:
            msg = f"Tick ID mismatch: expected {expected_tick_id}, got {tick_id}"
            raise BotProtocolError(msg)

        # Extract action fields with defaults
        desired_angle = action_dict.get("desired_turret_angle")
        # Convert JSON null to Python None, but keep numeric values
        if desired_angle is not None and not isinstance(desired_angle, (int, float)):
            desired_angle = None

        return BotAction(
            move_forward=action_dict.get("move_forward", False),
            move_backward=action_dict.get("move_backward", False),
            turn_left=action_dict.get("turn_left", False),
            turn_right=action_dict.get("turn_right", False),
            turret_left=action_dict.get("turret_left", False),
            turret_right=action_dict.get("turret_right", False),
            shoot=action_dict.get("shoot", False),
            desired_turret_angle=desired_angle,
        )

    def get_stats(self) -> dict:
        """Get runtime statistics for monitoring.

        Returns:
            Dict with tick_count, timeout_count, error_count.

        """
        return {
            "tick_count": self._tick_count,
            "timeout_count": self._timeout_count,
            "error_count": self._error_count,
        }

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        self.stop()
