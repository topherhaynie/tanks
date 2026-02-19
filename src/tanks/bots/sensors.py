"""Sensor API for bot inputs."""

import math
from typing import TYPE_CHECKING

from tanks.bots.bot_api import (
    BotState,
    FogMemorySummary,
    MapBounds,
    RadarHit,
    SelfState,
    VisibleEntity,
)
from tanks.config.constants import TILE_SIZE

if TYPE_CHECKING:
    from tanks.core.game import Game
    from tanks.entities.entity import Entity
    from tanks.entities.tank import Tank
    from tanks.perception.memory import TerrainMemory


def build_bot_state(tank: "Tank", game: "Game", tick_id: int, dt: float) -> BotState:
    """Build a bot state snapshot from game systems.

    Args:
        tank: Tank controlled by the bot.
        game: Game instance providing state and map data.
        tick_id: Input tick identifier.
        dt: Input tick duration in seconds.

    Returns:
        BotState snapshot for this tick.

    """
    map_width_px, map_height_px = _get_map_bounds(game)

    self_state = SelfState(
        id=tank.id,
        x=tank.x,
        y=tank.y,
        rotation=math.radians(tank.angle),
        turret_rotation=math.radians(tank.turret_angle),
        speed=tank.speed if hasattr(tank, "speed") else 0.0,
        hp=tank.hp,
        shoot_cooldown=tank.shoot_cooldown,
        missile_cooldown=tank.missile_cooldown,
        mine_cooldown=tank.mine_cooldown,
        mine_count=tank.mine_count,
        team=tank.team,
    )

    visible_entities = [
        _build_visible_entity(tank, entity) for entity in tank.visible_entities
    ]
    radar_hits = [
        _build_radar_hit(tank, entity)
        for entity, _distance, _angle_deg in tank.radar_detections
    ]

    fog_memory = _summarize_fog_memory(tank.fog_memory) if tank.fog_memory else None

    return BotState(
        tick_id=tick_id,
        dt=dt,
        self_state=self_state,
        visible_entities=visible_entities,
        radar_hits=radar_hits,
        fog_memory=fog_memory,
        map_bounds=MapBounds(width=map_width_px, height=map_height_px),
        tile_size=TILE_SIZE,
    )


def _get_map_bounds(game: "Game") -> tuple[int, int]:
    if not game.state.game_map:
        return 0, 0
    return game.state.game_map.get_pixel_size()


def _build_visible_entity(tank: "Tank", entity: "Entity") -> VisibleEntity:
    kind = _entity_kind(entity)
    rotation = _maybe_get_rotation(entity)
    turret_rotation = _maybe_get_turret_rotation(entity)
    team = _maybe_get_team(entity)

    dx = entity.x - tank.x
    dy = entity.y - tank.y
    distance = math.hypot(dx, dy)
    bearing = _relative_bearing(tank, dx, dy)

    return VisibleEntity(
        entity_id=entity.id,
        kind=kind,
        x=entity.x,
        y=entity.y,
        rotation=rotation,
        turret_rotation=turret_rotation,
        team=team,
        active=entity.active,
        distance=distance,
        bearing=bearing,
    )


def _build_radar_hit(tank: "Tank", entity: "Entity") -> RadarHit:
    dx = entity.x - tank.x
    dy = entity.y - tank.y
    distance = math.hypot(dx, dy)
    bearing = _relative_bearing(tank, dx, dy)

    return RadarHit(
        entity_id=entity.id,
        kind=_entity_kind(entity),
        distance=distance,
        bearing=bearing,
    )


def _relative_bearing(tank: "Tank", dx: float, dy: float) -> float:
    absolute_angle = math.atan2(dy, dx)
    tank_angle = math.radians(tank.angle)
    return math.atan2(
        math.sin(absolute_angle - tank_angle),
        math.cos(absolute_angle - tank_angle),
    )


def _entity_kind(entity: "Entity") -> str:
    name = type(entity).__name__.lower()
    if name == "tank":
        return "tank"
    if name == "mine":
        return "mine"
    if name == "missile":
        return "missile"
    if name == "bullet":
        return "bullet"
    return "obstacle"


def _maybe_get_rotation(entity: "Entity") -> float | None:
    if hasattr(entity, "angle"):
        return math.radians(entity.angle)
    return None


def _maybe_get_turret_rotation(entity: "Entity") -> float | None:
    if hasattr(entity, "turret_angle"):
        return math.radians(entity.turret_angle)
    return None


def _maybe_get_team(entity: "Entity") -> int | None:
    if hasattr(entity, "team"):
        return int(entity.team)
    return None


def _summarize_fog_memory(fog_memory: "TerrainMemory") -> FogMemorySummary:
    revealed_bounds: list[tuple[int, int, int, int]] = []

    for y in range(fog_memory.fog_height):
        run_start = None
        for x in range(fog_memory.fog_width):
            is_revealed = fog_memory.is_revealed(x, y)
            if is_revealed and run_start is None:
                run_start = x
            if not is_revealed and run_start is not None:
                revealed_bounds.append((run_start, y, x - run_start, 1))
                run_start = None
        if run_start is not None:
            revealed_bounds.append((run_start, y, fog_memory.fog_width - run_start, 1))

    return FogMemorySummary(revealed_bounds=revealed_bounds)
