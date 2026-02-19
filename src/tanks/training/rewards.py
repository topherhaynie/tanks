"""Reward functions for reinforcement learning.

Defines reward shaping and calculation for training RL agents.
"""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.bots.bot_api import BotState


@dataclass
class RewardWeights:
    """Configurable weights for reward components.

    All rewards can be tuned to balance learning objectives.
    """

    # Combat rewards
    bullet_hit: float = 10.0
    missile_hit: float = 15.0
    mine_kill: float = 20.0
    kill: float = 100.0
    death: float = -100.0
    bullet_hit_taken: float = -5.0
    missile_hit_taken: float = -10.0
    bullet_wasted: float = -1.0

    # Survival rewards
    survival_per_second: float = 0.1
    win_bonus: float = 50.0

    # Shaping rewards (optional - can be disabled)
    safe_distance: float = 1.0  # Maintaining good positioning
    good_cover: float = 2.0  # Being near cover
    facing_enemy: float = 1.0  # Facing visible enemy
    standing_still_penalty: float = -0.5  # Encourage movement
    standing_still_threshold_steps: int = 60  # Delay idle penalty until truly idle
    movement_progress: float = 0.1  # Reward meaningful movement per step
    approach_visible_enemy: float = 0.25  # Reward reducing distance to visible enemy
    approach_radar_enemy: float = 0.12  # Reward reducing distance to radar enemy
    new_terrain_revealed: float = 5.0  # Exploration bonus
    enemy_spotted: float = 8.0  # One-time bonus for acquiring first visual contact
    shot_with_enemy_visible: float = 0.5  # Encourage engagement once target found
    shot_without_enemy_visible: float = -0.1  # Discourage blind spam
    map_center_control: float = 3.0  # Controlling center
    cornered_penalty: float = -2.0  # Being trapped


@dataclass
class RewardEvent:
    """Represents a reward-generating event."""

    event_type: str
    reward: float
    metadata: dict[str, float | str] = field(default_factory=dict)


class RewardCalculator:
    """Calculates rewards for RL training.

    Tracks events during episodes and computes total rewards based on
    configurable weights. Supports both sparse rewards (kills, deaths) and
    dense reward shaping (positioning, exploration).
    """

    def __init__(
        self,
        weights: RewardWeights | None = None,
        enable_shaping: bool = True,
    ) -> None:
        """Initialize reward calculator.

        Args:
            weights: Reward weights configuration. Uses defaults if None.
            enable_shaping: Whether to include shaping rewards (positioning, exploration).

        """
        self.weights = weights or RewardWeights()
        self.enable_shaping = enable_shaping

        # Event tracking
        self.episode_rewards: list[RewardEvent] = []
        self.step_reward = 0.0

        # Previous state tracking for deltas
        self.prev_hp: int | None = None
        self.prev_kills = 0
        self.prev_shots_fired = 0
        self.prev_hits = 0
        self.prev_position: tuple[float, float] | None = None
        self.prev_explored_area = 0.0
        self.steps_stationary = 0
        self.enemy_spotted_once = False
        self.prev_visible_enemy_distance: float | None = None
        self.prev_radar_enemy_distance: float | None = None

    def reset(self) -> None:
        """Reset calculator for new episode."""
        self.episode_rewards.clear()
        self.step_reward = 0.0
        self.prev_hp = None
        self.prev_kills = 0
        self.prev_shots_fired = 0
        self.prev_hits = 0
        self.prev_position = None
        self.prev_explored_area = 0.0
        self.steps_stationary = 0
        self.enemy_spotted_once = False
        self.prev_visible_enemy_distance = None
        self.prev_radar_enemy_distance = None

    def compute_step_reward(
        self,
        state: "BotState",
        is_dead: bool = False,
        did_kill: bool = False,
        did_win: bool = False,
    ) -> float:
        """Compute reward for current step.

        Args:
            state: Current bot state.
            is_dead: Whether the bot died this step.
            did_kill: Whether the bot got a kill this step.
            did_win: Whether the bot won the match this step.

        Returns:
            Total reward for this step.

        """
        self.step_reward = 0.0

        # Death and kill rewards (sparse, high magnitude)
        if is_dead:
            self._add_reward("death", self.weights.death)

        if did_kill:
            self._add_reward("kill", self.weights.kill)

        if did_win:
            self._add_reward("win", self.weights.win_bonus)

        # Damage taken (HP delta)
        if self.prev_hp is not None and state.self_state.hp < self.prev_hp:
            damage_taken = self.prev_hp - state.self_state.hp
            # Assume bullet damage by default
            reward = damage_taken * self.weights.bullet_hit_taken
            self._add_reward("damage_taken", reward, {"damage": float(damage_taken)})

        self.prev_hp = state.self_state.hp

        # Survival reward (accumulates over time)
        survival_reward = self.weights.survival_per_second * state.dt
        self._add_reward("survival", survival_reward)

        # Shaping rewards (optional)
        if self.enable_shaping:
            self._compute_shaping_rewards(state)

        return self.step_reward

    def record_hit(self, weapon_type: str = "bullet") -> None:
        """Record a successful hit for reward tracking.

        Args:
            weapon_type: Type of weapon that hit ("bullet", "missile", "mine").

        """
        if weapon_type == "bullet":
            reward = self.weights.bullet_hit
        elif weapon_type == "missile":
            reward = self.weights.missile_hit
        elif weapon_type == "mine":
            reward = self.weights.mine_kill
        else:
            reward = self.weights.bullet_hit

        self._add_reward(f"{weapon_type}_hit", reward)

    def record_miss(self) -> None:
        """Record a missed shot for reward tracking."""
        self._add_reward("bullet_wasted", self.weights.bullet_wasted)

    def record_shot(self, enemy_visible: bool) -> None:
        """Record a shot event with engagement context.

        Args:
            enemy_visible: Whether at least one enemy tank was visible when firing.

        """
        if enemy_visible:
            self._add_reward("engage_visible_enemy", self.weights.shot_with_enemy_visible)
        else:
            self._add_reward("blind_fire", self.weights.shot_without_enemy_visible)

    def _compute_shaping_rewards(self, state: "BotState") -> None:
        """Compute dense shaping rewards for positioning and strategy.

        Args:
            state: Current bot state.

        """
        s = state.self_state

        # Check for new terrain revealed (exploration bonus)
        if state.fog_memory and state.fog_memory.revealed_bounds:
            current_area = sum(b[2] * b[3] for b in state.fog_memory.revealed_bounds)
            if current_area > self.prev_explored_area:
                area_delta = current_area - self.prev_explored_area
                # Normalize delta (1 fog tile = 1 area unit, give bonus per ~10 tiles)
                exploration_bonus = (area_delta / 10.0) * self.weights.new_terrain_revealed
                self._add_reward("exploration", exploration_bonus)
            self.prev_explored_area = current_area

        # Penalty for standing still too long
        if self.prev_position is not None:
            dx = s.x - self.prev_position[0]
            dy = s.y - self.prev_position[1]
            distance_moved = math.hypot(dx, dy)

            if distance_moved < 2.0:  # Moved less than 2 pixels
                self.steps_stationary += 1
                if self.steps_stationary > self.weights.standing_still_threshold_steps:
                    self._add_reward(
                        "standing_still",
                        self.weights.standing_still_penalty,
                    )
            else:
                self.steps_stationary = 0
                movement_bonus = min(distance_moved / 12.0, 1.0) * self.weights.movement_progress
                self._add_reward("movement_progress", movement_bonus)

        self.prev_position = (s.x, s.y)

        # Map center control bonus
        map_center_x = state.map_bounds.width / 2.0
        map_center_y = state.map_bounds.height / 2.0
        dist_to_center = ((s.x - map_center_x) ** 2 + (s.y - map_center_y) ** 2) ** 0.5
        max_dist = ((state.map_bounds.width / 2.0) ** 2 + (state.map_bounds.height / 2.0) ** 2) ** 0.5

        # Reward being near center (but not always - only give small bonus)
        if dist_to_center < max_dist * 0.3:  # Within 30% of center
            center_bonus = (
                (1.0 - dist_to_center / (max_dist * 0.3)) * self.weights.map_center_control * 0.1
            )  # Small per-step bonus
            self._add_reward("center_control", center_bonus)

        # Cornered penalty (near edge with low HP)
        edge_dist = min(
            s.x,
            s.y,
            state.map_bounds.width - s.x,
            state.map_bounds.height - s.y,
        )
        if edge_dist < 100 and s.hp <= 1:
            self._add_reward("cornered", self.weights.cornered_penalty)

        # Facing enemy bonus (encourage aiming)
        enemies = [e for e in state.visible_entities if e.kind == "tank" and e.team != s.team and e.active]
        if enemies and not self.enemy_spotted_once:
            self._add_reward("enemy_spotted", self.weights.enemy_spotted)
            self.enemy_spotted_once = True

        if enemies:
            nearest = min(enemies, key=lambda e: e.distance)
            nearest_distance = float(nearest.distance)

            if self.prev_visible_enemy_distance is not None:
                distance_delta = self.prev_visible_enemy_distance - nearest_distance
                if distance_delta > 0.0:
                    approach_bonus = min(distance_delta / 60.0, 1.0) * self.weights.approach_visible_enemy
                    self._add_reward("approach_visible_enemy", approach_bonus)

            self.prev_visible_enemy_distance = nearest_distance

            # Check if turret is roughly facing enemy (within 30 degrees)
            turret_to_enemy_diff = abs(nearest.bearing)
            if turret_to_enemy_diff < math.radians(30):
                facing_bonus = self.weights.facing_enemy * 0.1  # Small per-step bonus
                self._add_reward("facing_enemy", facing_bonus)
        else:
            self.prev_visible_enemy_distance = None

        # Approach bonus from radar when enemy is not currently visible
        if not enemies:
            radar_tank_distances = [float(hit.distance) for hit in state.radar_hits if hit.kind == "tank"]
            if radar_tank_distances:
                nearest_radar = min(radar_tank_distances)
                if self.prev_radar_enemy_distance is not None:
                    radar_delta = self.prev_radar_enemy_distance - nearest_radar
                    if radar_delta > 0.0:
                        radar_bonus = min(radar_delta / 120.0, 1.0) * self.weights.approach_radar_enemy
                        self._add_reward("approach_radar_enemy", radar_bonus)
                self.prev_radar_enemy_distance = nearest_radar
            else:
                self.prev_radar_enemy_distance = None
        else:
            self.prev_radar_enemy_distance = None

    def _add_reward(
        self,
        event_type: str,
        reward: float,
        metadata: dict | None = None,
    ) -> None:
        """Add a reward event.

        Args:
            event_type: Type of event generating reward.
            reward: Reward value.
            metadata: Optional event metadata.

        """
        self.step_reward += reward
        self.episode_rewards.append(
            RewardEvent(
                event_type=event_type,
                reward=reward,
                metadata=metadata or {},
            ),
        )

    def get_episode_summary(self) -> dict[str, float]:
        """Get summary statistics for episode rewards.

        Returns:
            Dictionary with reward breakdown by type.

        """
        summary: dict[str, float] = {}

        for event in self.episode_rewards:
            if event.event_type not in summary:
                summary[event.event_type] = 0.0
            summary[event.event_type] += event.reward

        summary["total"] = sum(summary.values())
        return summary

    def get_total_reward(self) -> float:
        """Get total episode reward.

        Returns:
            Sum of all rewards in episode.

        """
        return sum(event.reward for event in self.episode_rewards)


def create_sparse_reward_calculator() -> RewardCalculator:
    """Create reward calculator with sparse rewards only (no shaping).

    Good for initial training to learn basic behaviors without bias.

    Returns:
        RewardCalculator with shaping disabled.

    """
    return RewardCalculator(enable_shaping=False)


def create_shaped_reward_calculator(
    weights: RewardWeights | None = None,
) -> RewardCalculator:
    """Create reward calculator with dense shaping rewards.

    Good for accelerated learning with guidance on positioning and strategy.

    Args:
        weights: Custom reward weights. Uses defaults if None.

    Returns:
        RewardCalculator with shaping enabled.

    """
    return RewardCalculator(weights=weights, enable_shaping=True)
