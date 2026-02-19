"""A slightly smarter bot that uses radar and line-of-sight targeting."""

import math
import random

from tanks.bots.bot_api import BotAction, BotState, RadarHit, VisibleEntity

# Stuck detection constants
MIN_MOVEMENT_PX = 2.0  # Minimum movement to not be considered stuck
STUCK_TIMEOUT_SEC = 0.5  # Time before considering tank stuck
REVERSE_DURATION_SEC = 0.8  # How long to reverse when stuck

# Turning thresholds (radians)
PURSUIT_TURN_THRESHOLD = 0.10  # Turn threshold for radar pursuit
ATTACK_BODY_TURN_THRESHOLD = 0.12  # Body turn threshold when attacking
ATTACK_TURRET_AIM_THRESHOLD = 0.10  # Turret aim threshold for shooting

# Wander behavior
WANDER_INTERVAL_SEC = 2.0  # Time between direction changes


class SmartBot:
    """Bot that pursues radar targets and attacks visible enemies."""

    def __init__(self) -> None:
        """Initialize the smart bot."""
        self._wander_timer = 0.0
        self._turn_right = True
        self._stuck_timer = 0.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._reversing = False
        self._reverse_timer = 0.0
        self._rng = random.Random()  # noqa: S311

    def update(self, state: BotState) -> BotAction:
        """Compute actions from the current state.

        Args:
            state: Bot state snapshot.

        Returns:
            BotAction describing the bot's input intent.

        """
        target = _select_nearest_visible_enemy(state)
        if target is not None:
            return _attack_target(state, target)

        radar_target = _select_nearest_radar_target(state)
        if radar_target is not None:
            return self._pursue_radar_hit(state, radar_target)

        return self._wander(state)

    def _is_stuck(self, state: BotState) -> bool:
        dx = state.self_state.x - self._last_x
        dy = state.self_state.y - self._last_y
        movement = math.hypot(dx, dy)

        if movement < MIN_MOVEMENT_PX:
            self._stuck_timer += state.dt
        else:
            self._stuck_timer = 0.0

        self._last_x = state.self_state.x
        self._last_y = state.self_state.y

        return self._stuck_timer > STUCK_TIMEOUT_SEC

    def _pursue_radar_hit(self, state: BotState, hit: RadarHit) -> BotAction:
        if self._is_stuck(state):
            self._reversing = True
            self._reverse_timer = REVERSE_DURATION_SEC

        if self._reversing:
            self._reverse_timer -= state.dt
            if self._reverse_timer <= 0:
                self._reversing = False
                self._stuck_timer = 0.0
                self._turn_right = self._rng.choice([True, False])

            return BotAction(
                move_backward=True,
                turn_left=self._turn_right,
                turn_right=not self._turn_right,
            )

        desired_angle = _normalize_angle(state.self_state.rotation + hit.bearing)
        body_diff = _angle_diff(desired_angle, state.self_state.rotation)

        turn_right = body_diff > PURSUIT_TURN_THRESHOLD
        turn_left = body_diff < -PURSUIT_TURN_THRESHOLD

        return BotAction(
            move_forward=True,
            turn_left=turn_left,
            turn_right=turn_right,
            desired_turret_angle=desired_angle,
        )

    def _wander(self, state: BotState) -> BotAction:
        if self._is_stuck(state):
            self._reversing = True
            self._reverse_timer = REVERSE_DURATION_SEC

        if self._reversing:
            self._reverse_timer -= state.dt
            if self._reverse_timer <= 0:
                self._reversing = False
                self._stuck_timer = 0.0
                self._turn_right = self._rng.choice([True, False])

            return BotAction(
                move_backward=True,
                turn_left=self._turn_right,
                turn_right=not self._turn_right,
            )

        self._wander_timer += state.dt
        if self._wander_timer > WANDER_INTERVAL_SEC:
            self._wander_timer = 0.0
            self._turn_right = not self._turn_right

        return BotAction(
            move_forward=True,
            turn_left=not self._turn_right,
            turn_right=self._turn_right,
        )


def _select_nearest_visible_enemy(state: BotState) -> VisibleEntity | None:
    best = None
    best_distance = None
    for entity in state.visible_entities:
        if entity.kind != "tank" or entity.team == state.self_state.team:
            continue
        if best_distance is None or entity.distance < best_distance:
            best = entity
            best_distance = entity.distance
    return best


def _select_nearest_radar_target(state: BotState) -> RadarHit | None:
    best = None
    best_distance = None
    for hit in state.radar_hits:
        if hit.kind != "tank":
            continue
        if best_distance is None or hit.distance < best_distance:
            best = hit
            best_distance = hit.distance
    return best


def _attack_target(state: BotState, target: VisibleEntity) -> BotAction:
    dx = target.x - state.self_state.x
    dy = target.y - state.self_state.y
    desired_angle = math.atan2(dy, dx)

    body_diff = _angle_diff(desired_angle, state.self_state.rotation)
    turret_diff = _angle_diff(desired_angle, state.self_state.turret_rotation)

    turn_right = body_diff > ATTACK_BODY_TURN_THRESHOLD
    turn_left = body_diff < -ATTACK_BODY_TURN_THRESHOLD
    shoot = (
        abs(turret_diff) < ATTACK_TURRET_AIM_THRESHOLD
        and state.self_state.shoot_cooldown <= 0.0
    )

    return BotAction(
        move_forward=True,
        turn_left=turn_left,
        turn_right=turn_right,
        shoot=shoot,
        desired_turret_angle=desired_angle,
    )


def _angle_diff(target: float, current: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))


def _normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))
