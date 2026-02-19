"""Simple example bot implementation."""

import math
import random

from tanks.bots.bot_api import BotAction, BotState, VisibleEntity


class SimpleBot:
    """A basic bot that seeks visible enemies and wanders otherwise."""

    def __init__(self) -> None:
        """Initialize the simple bot."""
        self._wander_timer = 0.0
        self._turn_right = True
        self._wander_interval = 2.5
        self._rng = random.Random()

    def update(self, state: BotState) -> BotAction:
        """Compute actions from the current state.

        Args:
            state: Bot state snapshot.

        Returns:
            BotAction describing the bot's input intent.

        """
        target = _select_nearest_enemy(state)
        if target is not None:
            aim_noise = self._rng.uniform(-0.08, 0.08)
            return _attack_target(state, target, aim_noise)

        self._wander_timer += state.dt
        if self._wander_timer > self._wander_interval:
            self._wander_timer = 0.0
            self._turn_right = not self._turn_right
            self._wander_interval = max(1.2, 2.5 + self._rng.uniform(-0.8, 0.8))

        return BotAction(
            move_forward=True,
            turn_right=self._turn_right,
            turn_left=not self._turn_right,
        )


def _select_nearest_enemy(state: BotState) -> VisibleEntity | None:
    best = None
    best_distance = None
    for entity in state.visible_entities:
        if entity.kind != "tank" or entity.team == state.self_state.team:
            continue
        if best_distance is None or entity.distance < best_distance:
            best = entity
            best_distance = entity.distance
    return best


def _attack_target(state: BotState, target: VisibleEntity, aim_noise: float) -> BotAction:
    dx = target.x - state.self_state.x
    dy = target.y - state.self_state.y
    desired_angle = math.atan2(dy, dx) + aim_noise

    body_diff = _angle_diff(desired_angle, state.self_state.rotation)
    turret_diff = _angle_diff(desired_angle, state.self_state.turret_rotation)

    turn_right = body_diff > 0.15
    turn_left = body_diff < -0.15

    shoot = abs(turret_diff) < 0.12 and state.self_state.shoot_cooldown <= 0.0

    return BotAction(
        move_forward=True,
        turn_left=turn_left,
        turn_right=turn_right,
        shoot=shoot,
        desired_turret_angle=desired_angle,
    )


def _angle_diff(target: float, current: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))
