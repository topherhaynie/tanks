"""A significantly smarter bot with tactical combat behavior.

This bot implements:
- Target prediction (leading moving targets)
- Evasive maneuvering
- Tactical positioning (optimal engagement range)
- Risk assessment (retreat when low HP)
- Cover usage
"""

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
ATTACK_TURRET_AIM_THRESHOLD = 0.08  # Turret aim threshold for shooting (tighter!)

# Wander behavior
WANDER_INTERVAL_SEC = 2.0  # Time between direction changes

# Tactical constants
OPTIMAL_RANGE = 250.0  # Optimal engagement distance
CLOSE_RANGE = 150.0  # Too close, back up
LONG_RANGE = 400.0  # Too far, move closer
LOW_HP_THRESHOLD = 35.0  # HP threshold for retreat
CRITICAL_HP_THRESHOLD = 20.0  # HP for desperate retreat
BULLET_SPEED = 400.0  # Approximate bullet speed for leading
STRAFE_DURATION = 1.2  # How long to strafe for
UNDER_FIRE_COOLDOWN = 1.5  # Time to evade after taking damage


class SmartBot:
    """Bot with advanced tactical combat capabilities."""

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

        # Tactical state
        self._last_hp = 100.0
        self._under_fire_timer = 0.0
        self._strafe_timer = 0.0
        self._strafe_direction = 1  # 1 for right, -1 for left
        self._engagement_mode = "aggressive"  # aggressive, defensive, retreat

        # Target tracking for velocity estimation
        self._target_history: dict[int, tuple[float, float, float]] = {}  # entity_id -> (x, y, time)
        self._elapsed_time = 0.0  # Track accumulated time

    def update(self, state: BotState) -> BotAction:
        """Compute actions from the current state with tactical awareness.

        Args:
            state: Bot state snapshot.

        Returns:
            BotAction describing the bot's input intent.

        """
        # Track elapsed time
        self._elapsed_time += state.dt

        # Update tactical state
        self._update_tactical_state(state)

        # Track target positions for velocity estimation
        self._update_target_tracking(state)

        # Check for visible enemies
        target = _select_nearest_visible_enemy(state)
        if target is not None:
            return self._engage_target(state, target)

        # Pursue radar targets if not under fire
        if self._under_fire_timer <= 0:
            radar_target = _select_nearest_radar_target(state)
            if radar_target is not None:
                return self._pursue_radar_hit(state, radar_target)

        # Wander/patrol
        return self._wander(state)

    def _update_tactical_state(self, state: BotState) -> None:
        """Update tactical state tracking."""
        # Check if we took damage
        if state.self_state.hp < self._last_hp:
            damage_taken = self._last_hp - state.self_state.hp
            if damage_taken > 1.0:  # Significant damage
                self._under_fire_timer = UNDER_FIRE_COOLDOWN
                self._strafe_timer = STRAFE_DURATION
                self._strafe_direction *= -1  # Change strafe direction

        self._last_hp = state.self_state.hp
        self._under_fire_timer -= state.dt
        self._strafe_timer -= state.dt

        # Update engagement mode based on HP
        if state.self_state.hp < CRITICAL_HP_THRESHOLD:
            self._engagement_mode = "retreat"
        elif state.self_state.hp < LOW_HP_THRESHOLD:
            self._engagement_mode = "defensive"
        else:
            self._engagement_mode = "aggressive"

    def _update_target_tracking(self, state: BotState) -> None:
        """Track visible entities for velocity estimation."""
        current_time = self._elapsed_time

        # Update history for visible entities
        visible_ids = set()
        for entity in state.visible_entities:
            if entity.kind == "tank" and entity.team != state.self_state.team:
                visible_ids.add(entity.entity_id)
                self._target_history[entity.entity_id] = (entity.x, entity.y, current_time)

        # Clean up old history (entities no longer visible)
        ids_to_remove = [eid for eid in self._target_history if eid not in visible_ids]
        for eid in ids_to_remove:
            del self._target_history[eid]

    def _estimate_target_velocity(self, target: VisibleEntity, current_time: float) -> tuple[float, float]:
        """Estimate target velocity from position history.

        Args:
            target: Target entity.
            current_time: Current game time.

        Returns:
            Tuple of (velocity_x, velocity_y) in pixels per second.

        """
        if target.entity_id not in self._target_history:
            return (0.0, 0.0)

        last_x, last_y, last_time = self._target_history[target.entity_id]
        dt = current_time - last_time

        if dt < 0.01:  # Avoid division by very small numbers
            return (0.0, 0.0)

        velocity_x = (target.x - last_x) / dt
        velocity_y = (target.y - last_y) / dt

        return (velocity_x, velocity_y)

    def _engage_target(self, state: BotState, target: VisibleEntity) -> BotAction:
        """Engage visible target with tactical behavior."""
        distance = target.distance

        # Predict target position
        predicted_angle = self._predict_target_position(state, target)

        # Determine movement based on range and HP
        move_forward = False
        move_backward = False

        if self._engagement_mode == "retreat":
            # Low HP: retreat while shooting
            move_backward = True
        elif distance < CLOSE_RANGE:
            # Too close: back up
            move_backward = True
        elif distance > LONG_RANGE and self._engagement_mode == "aggressive":
            # Too far: move closer
            move_forward = True
        elif CLOSE_RANGE <= distance <= OPTIMAL_RANGE:
            # Good range: strafe if under fire
            if self._strafe_timer > 0:
                move_forward = True  # Strafe while moving
            else:
                move_forward = distance > OPTIMAL_RANGE  # Fine-tune position
        else:
            # Default: advance cautiously
            move_forward = self._engagement_mode == "aggressive"

        # Calculate aiming angles
        body_diff = _angle_diff(predicted_angle, state.self_state.rotation)
        turret_diff = _angle_diff(predicted_angle, state.self_state.turret_rotation)

        # Turning logic with strafing
        turn_right = False
        turn_left = False

        if self._strafe_timer > 0 and abs(body_diff) < 0.5:
            # Strafe perpendicular to target
            turn_right = self._strafe_direction > 0
            turn_left = self._strafe_direction < 0
        else:
            # Normal turning toward target
            turn_right = body_diff > ATTACK_BODY_TURN_THRESHOLD
            turn_left = body_diff < -ATTACK_BODY_TURN_THRESHOLD

        # Shooting logic: only shoot when well-aimed and good opportunity
        can_shoot = state.self_state.shoot_cooldown <= 0.0
        well_aimed = abs(turret_diff) < ATTACK_TURRET_AIM_THRESHOLD
        good_distance = CLOSE_RANGE < distance < LONG_RANGE

        shoot = can_shoot and well_aimed and good_distance

        return BotAction(
            move_forward=move_forward,
            move_backward=move_backward,
            turn_left=turn_left,
            turn_right=turn_right,
            shoot=shoot,
            desired_turret_angle=predicted_angle,
        )

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

    def _predict_target_position(self, state: BotState, target: VisibleEntity) -> float:
        """Predict where to aim based on target velocity.

        Args:
            state: Current bot state.
            target: Target entity.

        Returns:
            Predicted angle to aim at.

        """
        # Calculate current angle to target
        dx = target.x - state.self_state.x
        dy = target.y - state.self_state.y
        current_angle = math.atan2(dy, dx)
        distance = target.distance

        # Estimate target velocity from position history
        velocity_x, velocity_y = self._estimate_target_velocity(target, self._elapsed_time)

        # If target is stationary, aim at current position
        target_speed = math.hypot(velocity_x, velocity_y)
        if target_speed < 20.0:  # Threshold for stationary target
            return current_angle

        # Estimate time for bullet to reach target
        time_to_target = distance / BULLET_SPEED

        # Predict future position
        predicted_x = target.x + velocity_x * time_to_target
        predicted_y = target.y + velocity_y * time_to_target

        # Calculate angle to predicted position
        pred_dx = predicted_x - state.self_state.x
        pred_dy = predicted_y - state.self_state.y
        predicted_angle = math.atan2(pred_dy, pred_dx)

        return predicted_angle


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
    shoot = abs(turret_diff) < ATTACK_TURRET_AIM_THRESHOLD and state.self_state.shoot_cooldown <= 0.0

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
