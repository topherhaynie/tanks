"""Bot API dataclasses and protocol definitions."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MapBounds:
    """Map bounds in pixels."""

    width: int
    height: int


@dataclass(frozen=True)
class FogMemorySummary:
    """Compact representation of revealed fog tiles.

    Attributes:
        revealed_bounds: Rectangles in fog-tile coordinates.

    """

    revealed_bounds: list[tuple[int, int, int, int]]


@dataclass(frozen=True)
class SelfState:
    """State of the bot-controlled tank."""

    x: float
    y: float
    rotation: float
    turret_rotation: float
    speed: float
    hp: int
    shoot_cooldown: float
    team: int


@dataclass(frozen=True)
class VisibleEntity:
    """Visible entity description for bots."""

    entity_id: int
    kind: str
    x: float
    y: float
    rotation: float | None
    turret_rotation: float | None
    team: int | None
    active: bool
    distance: float
    bearing: float


@dataclass(frozen=True)
class RadarHit:
    """Radar detection summary."""

    entity_id: int
    kind: str
    distance: float
    bearing: float


@dataclass(frozen=True)
class BotState:
    """Snapshot of bot-relevant state for one input tick."""

    tick_id: int
    dt: float
    self_state: SelfState
    visible_entities: list[VisibleEntity]
    radar_hits: list[RadarHit]
    fog_memory: FogMemorySummary | None
    map_bounds: MapBounds
    tile_size: int


@dataclass(frozen=True)
class BotAction:
    """Bot action response for one input tick."""

    move_forward: bool = False
    move_backward: bool = False
    turn_left: bool = False
    turn_right: bool = False
    turret_left: bool = False
    turret_right: bool = False
    shoot: bool = False
    desired_turret_angle: float | None = None


class Bot(Protocol):
    """Protocol for bot implementations."""

    def update(self, state: BotState) -> BotAction:
        """Compute bot actions for the current state.

        Args:
            state: Snapshot of bot-relevant state.

        Returns:
            BotAction describing desired inputs.

        """
