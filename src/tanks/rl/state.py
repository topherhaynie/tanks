"""State representation for reinforcement learning.

Converts BotState sensor data into fixed-size vectors suitable for neural networks.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from tanks.bots.bot_api import BotState


class StateEncoder:
    """Encodes BotState into fixed-size vector for neural networks.

    State vector (78 dimensions):
    - Self state (7): x, y, angle, turret_angle, hp, velocity, angular_velocity
    - Weapon state (5): bullet_cooldown, missile_cooldown, mine_cooldown,
                        mine_count, ammo_state
    - Nearest enemy (8): distance, bearing, angle, hp, velocity, vx, vy, visible
    - Nearest bullet (5): distance, bearing, velocity, vx, vy
    - Nearest mine (3): distance, bearing, armed
    - Radar summary (10): count per octant (N, NE, E, SE, S, SW, W, NW),
                          avg_distance, closest_distance
    - Fog summary (8): revealed_fraction, center_x, center_y, bounds_min_x,
                       bounds_min_y, bounds_max_x, bounds_max_y, explored_area
    - Wall proximity (8): N, NE, E, SE, S, SW, W, NW distances to nearest wall
    - Recent damage (4): damage_dealt_1s, damage_taken_1s, shots_fired_1s,
                         hits_1s
    - Strategic (10): map_center_distance, edge_distance, enemy_los_count,
                      cover_quality, time_alive, kills, deaths, accuracy,
                      aggression_score, defensive_score
    - Tactical flags (10): under_fire, low_hp, enemy_visible, enemy_close,
                           mine_available, missile_available, stuck, cornered,
                           advantageous_position, retreat_needed

    All values are normalized to roughly [-1, 1] or [0, 1] ranges.
    """

    # State vector dimensions
    DIM_SELF = 7
    DIM_WEAPONS = 5
    DIM_NEAREST_ENEMY = 8
    DIM_NEAREST_BULLET = 5
    DIM_NEAREST_MINE = 3
    DIM_RADAR = 10
    DIM_FOG = 8
    DIM_WALLS = 8
    DIM_RECENT_DAMAGE = 4
    DIM_STRATEGIC = 10
    DIM_TACTICAL = 10

    TOTAL_DIM = (
        DIM_SELF
        + DIM_WEAPONS
        + DIM_NEAREST_ENEMY
        + DIM_NEAREST_BULLET
        + DIM_NEAREST_MINE
        + DIM_RADAR
        + DIM_FOG
        + DIM_WALLS
        + DIM_RECENT_DAMAGE
        + DIM_STRATEGIC
        + DIM_TACTICAL
    )

    def __init__(
        self, max_map_width: float = 2560.0, max_map_height: float = 1408.0
    ) -> None:
        """Initialize state encoder.

        Args:
            max_map_width: Maximum expected map width for normalization.
            max_map_height: Maximum expected map height for normalization.

        """
        self.max_map_width = max_map_width
        self.max_map_height = max_map_height
        self.max_distance = math.hypot(max_map_width, max_map_height)

        # History tracking for strategic metrics
        self.damage_dealt_history: list[tuple[float, float]] = []  # (time, damage)
        self.damage_taken_history: list[tuple[float, float]] = []
        self.shots_fired_history: list[tuple[float, int]] = []
        self.hits_history: list[tuple[float, int]] = []
        self.total_kills = 0
        self.total_deaths = 0
        self.birth_time = 0.0
        self.current_time = 0.0
        self.last_position: tuple[float, float] | None = None
        self.stuck_counter = 0

    def encode(self, state: "BotState") -> np.ndarray:
        """Encode BotState into fixed-size vector.

        Args:
            state: Current bot state snapshot.

        Returns:
            Numpy array of shape (78,) with normalized state values.

        """
        self.current_time += state.dt

        vector = np.zeros(self.TOTAL_DIM, dtype=np.float32)
        offset = 0

        # Self state (7)
        vector[offset : offset + self.DIM_SELF] = self._encode_self_state(state)
        offset += self.DIM_SELF

        # Weapon state (5)
        vector[offset : offset + self.DIM_WEAPONS] = self._encode_weapon_state(state)
        offset += self.DIM_WEAPONS

        # Nearest enemy (8)
        vector[offset : offset + self.DIM_NEAREST_ENEMY] = self._encode_nearest_enemy(
            state
        )
        offset += self.DIM_NEAREST_ENEMY

        # Nearest bullet (5)
        vector[offset : offset + self.DIM_NEAREST_BULLET] = self._encode_nearest_bullet(
            state
        )
        offset += self.DIM_NEAREST_BULLET

        # Nearest mine (3)
        vector[offset : offset + self.DIM_NEAREST_MINE] = self._encode_nearest_mine(
            state
        )
        offset += self.DIM_NEAREST_MINE

        # Radar summary (10)
        vector[offset : offset + self.DIM_RADAR] = self._encode_radar_summary(state)
        offset += self.DIM_RADAR

        # Fog summary (8)
        vector[offset : offset + self.DIM_FOG] = self._encode_fog_summary(state)
        offset += self.DIM_FOG

        # Wall proximity (8) - placeholder for now
        vector[offset : offset + self.DIM_WALLS] = np.ones(self.DIM_WALLS) * 0.5
        offset += self.DIM_WALLS

        # Recent damage (4)
        vector[offset : offset + self.DIM_RECENT_DAMAGE] = self._encode_recent_damage()
        offset += self.DIM_RECENT_DAMAGE

        # Strategic (10)
        vector[offset : offset + self.DIM_STRATEGIC] = self._encode_strategic(state)
        offset += self.DIM_STRATEGIC

        # Tactical flags (10)
        vector[offset : offset + self.DIM_TACTICAL] = self._encode_tactical_flags(state)
        offset += self.DIM_TACTICAL

        # Update position tracking for stuck detection
        self._update_position_tracking(state)

        return vector

    def _encode_self_state(self, state: "BotState") -> np.ndarray:
        """Encode self state (7 dims)."""
        s = state.self_state
        return np.array(
            [
                s.x / self.max_map_width,  # x position [0, 1]
                s.y / self.max_map_height,  # y position [0, 1]
                math.cos(s.rotation),  # body angle cos [-1, 1]
                math.sin(s.rotation),  # body angle sin [-1, 1]
                math.cos(s.turret_rotation),  # turret cos [-1, 1]
                math.sin(s.turret_rotation),  # turret sin [-1, 1]
                s.hp / 3.0,  # hp normalized [0, 1] (assuming max hp = 3)
            ],
            dtype=np.float32,
        )

    def _encode_weapon_state(self, state: "BotState") -> np.ndarray:
        """Encode weapon state (5 dims)."""
        s = state.self_state
        return np.array(
            [
                1.0 if s.shoot_cooldown <= 0 else 0.0,  # bullet ready
                s.shoot_cooldown / 0.5,  # bullet cooldown normalized
                1.0 if s.missile_cooldown <= 0 else 0.0,  # missile ready
                s.mine_cooldown / 5.0,  # mine cooldown normalized
                s.mine_count / 3.0,  # mine count [0, 1]
            ],
            dtype=np.float32,
        )

    def _encode_nearest_enemy(self, state: "BotState") -> np.ndarray:
        """Encode nearest enemy tank (8 dims)."""
        enemies = [
            e
            for e in state.visible_entities
            if e.kind == "tank" and e.team != state.self_state.team and e.active
        ]

        if not enemies:
            return np.zeros(8, dtype=np.float32)

        nearest = min(enemies, key=lambda e: e.distance)
        # Estimate velocity from rotation (rough approximation)
        vx = math.cos(nearest.rotation) * 100 if nearest.rotation is not None else 0.0
        vy = math.sin(nearest.rotation) * 100 if nearest.rotation is not None else 0.0

        return np.array(
            [
                nearest.distance / self.max_distance,  # distance [0, 1]
                math.cos(nearest.bearing),  # bearing cos [-1, 1]
                math.sin(nearest.bearing),  # bearing sin [-1, 1]
                (
                    math.cos(nearest.rotation) if nearest.rotation is not None else 0.0
                ),  # enemy angle cos
                (
                    math.sin(nearest.rotation) if nearest.rotation is not None else 0.0
                ),  # enemy angle sin
                vx / 100.0,  # estimated vx normalized
                vy / 100.0,  # estimated vy normalized
                1.0,  # visible flag
            ],
            dtype=np.float32,
        )

    def _encode_nearest_bullet(self, state: "BotState") -> np.ndarray:
        """Encode nearest bullet (5 dims)."""
        bullets = [e for e in state.visible_entities if e.kind == "bullet" and e.active]

        if not bullets:
            return np.zeros(5, dtype=np.float32)

        nearest = min(bullets, key=lambda e: e.distance)
        # Estimate velocity from rotation (bullets move fast)
        vx = math.cos(nearest.rotation) * 400 if nearest.rotation is not None else 0.0
        vy = math.sin(nearest.rotation) * 400 if nearest.rotation is not None else 0.0

        return np.array(
            [
                nearest.distance / 600.0,  # distance normalized to radar range
                math.cos(nearest.bearing),  # bearing cos
                math.sin(nearest.bearing),  # bearing sin
                vx / 400.0,  # vx normalized
                vy / 400.0,  # vy normalized
            ],
            dtype=np.float32,
        )

    def _encode_nearest_mine(self, state: "BotState") -> np.ndarray:
        """Encode nearest mine (3 dims)."""
        mines = [e for e in state.visible_entities if e.kind == "mine" and e.active]

        if not mines:
            return np.zeros(3, dtype=np.float32)

        nearest = min(mines, key=lambda e: e.distance)

        return np.array(
            [
                nearest.distance / 100.0,  # distance normalized
                math.cos(nearest.bearing),  # bearing cos
                math.sin(nearest.bearing),  # bearing sin
            ],
            dtype=np.float32,
        )

    def _encode_radar_summary(self, state: "BotState") -> np.ndarray:
        """Encode radar summary (10 dims).

        Divides radar into 8 octants and counts entities in each.
        """
        octant_counts = np.zeros(8, dtype=np.float32)

        if not state.radar_hits:
            return np.concatenate([octant_counts, [0.0, 1.0]])

        for hit in state.radar_hits:
            # Convert bearing to octant (0=N, 1=NE, 2=E, ..., 7=NW)
            angle_deg = math.degrees(hit.bearing) % 360
            octant = int((angle_deg + 22.5) / 45.0) % 8
            octant_counts[octant] += 1

        # Normalize counts (assume max 5 enemies per octant)
        octant_counts = np.clip(octant_counts / 5.0, 0.0, 1.0)

        # Compute average and closest distance
        distances = [hit.distance for hit in state.radar_hits]
        avg_distance = np.mean(distances) / 600.0  # Normalize to radar range
        closest_distance = min(distances) / 600.0

        return np.concatenate([octant_counts, [avg_distance, closest_distance]])

    def _encode_fog_summary(self, state: "BotState") -> np.ndarray:
        """Encode fog memory summary (8 dims)."""
        if not state.fog_memory or not state.fog_memory.revealed_bounds:
            return np.zeros(8, dtype=np.float32)

        # Compute bounding box of revealed area
        all_bounds = state.fog_memory.revealed_bounds
        min_x = min(b[0] for b in all_bounds)
        min_y = min(b[1] for b in all_bounds)
        max_x = max(b[0] + b[2] for b in all_bounds)
        max_y = max(b[1] + b[3] for b in all_bounds)

        # Compute center and area
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        explored_area = sum(b[2] * b[3] for b in all_bounds)

        # Estimate total map area in fog tiles (assuming 16px fog tiles)
        map_fog_width = state.map_bounds.width / 16
        map_fog_height = state.map_bounds.height / 16
        total_area = map_fog_width * map_fog_height
        revealed_fraction = (
            min(explored_area / total_area, 1.0) if total_area > 0 else 0.0
        )

        return np.array(
            [
                revealed_fraction,  # [0, 1]
                center_x / map_fog_width,  # normalized center x
                center_y / map_fog_height,  # normalized center y
                min_x / map_fog_width,  # normalized bounds
                min_y / map_fog_height,
                max_x / map_fog_width,
                max_y / map_fog_height,
                explored_area / total_area,  # normalized explored area
            ],
            dtype=np.float32,
        )

    def _encode_recent_damage(self) -> np.ndarray:
        """Encode recent damage metrics (4 dims)."""
        # Filter last 1 second of history
        cutoff = self.current_time - 1.0

        damage_dealt = sum(d for t, d in self.damage_dealt_history if t >= cutoff)
        damage_taken = sum(d for t, d in self.damage_taken_history if t >= cutoff)
        shots_fired = sum(s for t, s in self.shots_fired_history if t >= cutoff)
        hits = sum(h for t, h in self.hits_history if t >= cutoff)

        return np.array(
            [
                damage_dealt / 10.0,  # normalize (max ~10 dmg/s)
                damage_taken / 10.0,
                shots_fired / 10.0,  # max ~10 shots/s
                hits / 10.0,
            ],
            dtype=np.float32,
        )

    def _encode_strategic(self, state: "BotState") -> np.ndarray:
        """Encode strategic metrics (10 dims)."""
        s = state.self_state

        # Map center distance
        center_x = state.map_bounds.width / 2.0
        center_y = state.map_bounds.height / 2.0
        map_center_dist = math.hypot(s.x - center_x, s.y - center_y) / self.max_distance

        # Edge distance (distance to nearest edge)
        edge_dist = min(
            s.x, s.y, state.map_bounds.width - s.x, state.map_bounds.height - s.y
        )
        edge_dist_norm = edge_dist / (
            min(state.map_bounds.width, state.map_bounds.height) / 2.0
        )

        # Enemy LOS count
        enemy_los_count = len(
            [
                e
                for e in state.visible_entities
                if e.kind == "tank" and e.team != s.team and e.active
            ]
        )

        # Cover quality (placeholder - would need wall proximity)
        cover_quality = 0.5

        # Time alive
        time_alive = self.current_time - self.birth_time

        # Accuracy
        total_shots = sum(s for _, s in self.shots_fired_history)
        total_hits = sum(h for _, h in self.hits_history)
        accuracy = total_hits / total_shots if total_shots > 0 else 0.0

        # Aggression/defensive scores (placeholder)
        aggression_score = 0.5
        defensive_score = 0.5

        return np.array(
            [
                map_center_dist,  # [0, 1]
                edge_dist_norm,  # [0, 1]
                enemy_los_count / 5.0,  # normalize (max 5 enemies)
                cover_quality,  # [0, 1]
                min(time_alive / 100.0, 1.0),  # cap at 100s
                self.total_kills / 10.0,  # normalize
                self.total_deaths / 10.0,
                accuracy,  # [0, 1]
                aggression_score,  # [0, 1]
                defensive_score,  # [0, 1]
            ],
            dtype=np.float32,
        )

    def _encode_tactical_flags(self, state: "BotState") -> np.ndarray:
        """Encode tactical binary flags (10 dims)."""
        s = state.self_state

        # Under fire (detected bullets nearby)
        bullets_nearby = any(
            e.distance < 100 for e in state.visible_entities if e.kind == "bullet"
        )

        # Low HP
        low_hp = s.hp <= 1

        # Enemy visible
        enemy_visible = any(
            e.kind == "tank" and e.team != s.team and e.active
            for e in state.visible_entities
        )

        # Enemy close
        enemy_close = any(
            e.kind == "tank" and e.team != s.team and e.active and e.distance < 200
            for e in state.visible_entities
        )

        # Weapons available
        mine_available = s.mine_count > 0 and s.mine_cooldown <= 0
        missile_available = s.missile_cooldown <= 0

        # Stuck (not moving much)
        stuck = self.stuck_counter > 10

        # Cornered (near edge with low hp)
        edge_dist = min(
            s.x, s.y, state.map_bounds.width - s.x, state.map_bounds.height - s.y
        )
        cornered = edge_dist < 100 and low_hp

        # Advantageous position (placeholder)
        advantageous = False

        # Retreat needed
        retreat_needed = low_hp and enemy_close

        return np.array(
            [
                float(bullets_nearby),
                float(low_hp),
                float(enemy_visible),
                float(enemy_close),
                float(mine_available),
                float(missile_available),
                float(stuck),
                float(cornered),
                float(advantageous),
                float(retreat_needed),
            ],
            dtype=np.float32,
        )

    def _update_position_tracking(self, state: "BotState") -> None:
        """Update position tracking for stuck detection."""
        s = state.self_state
        current_pos = (s.x, s.y)

        if self.last_position is not None:
            dist_moved = math.hypot(
                current_pos[0] - self.last_position[0],
                current_pos[1] - self.last_position[1],
            )
            if dist_moved < 1.0:  # Moved less than 1 pixel
                self.stuck_counter += 1
            else:
                self.stuck_counter = max(0, self.stuck_counter - 1)

        self.last_position = current_pos

    def record_damage_dealt(self, damage: float) -> None:
        """Record damage dealt for metrics tracking."""
        self.damage_dealt_history.append((self.current_time, damage))
        # Keep only last 5 seconds
        cutoff = self.current_time - 5.0
        self.damage_dealt_history = [
            (t, d) for t, d in self.damage_dealt_history if t >= cutoff
        ]

    def record_damage_taken(self, damage: float) -> None:
        """Record damage taken for metrics tracking."""
        self.damage_taken_history.append((self.current_time, damage))
        cutoff = self.current_time - 5.0
        self.damage_taken_history = [
            (t, d) for t, d in self.damage_taken_history if t >= cutoff
        ]

    def record_shot_fired(self) -> None:
        """Record shot fired for accuracy tracking."""
        self.shots_fired_history.append((self.current_time, 1))
        cutoff = self.current_time - 5.0
        self.shots_fired_history = [
            (t, s) for t, s in self.shots_fired_history if t >= cutoff
        ]

    def record_hit(self) -> None:
        """Record successful hit for accuracy tracking."""
        self.hits_history.append((self.current_time, 1))
        cutoff = self.current_time - 5.0
        self.hits_history = [(t, h) for t, h in self.hits_history if t >= cutoff]

    def record_kill(self) -> None:
        """Record kill for stats tracking."""
        self.total_kills += 1

    def record_death(self) -> None:
        """Record death for stats tracking."""
        self.total_deaths += 1

    def reset(self) -> None:
        """Reset encoder state for new episode."""
        self.damage_dealt_history.clear()
        self.damage_taken_history.clear()
        self.shots_fired_history.clear()
        self.hits_history.clear()
        self.total_kills = 0
        self.total_deaths = 0
        self.birth_time = self.current_time
        self.last_position = None
        self.stuck_counter = 0
