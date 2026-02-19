# Bot API and Protocol (Draft)

This document defines the in-process Python bot API and the external bot protocol
for non-Python bots (e.g., C++). The goal is determinism, fairness, and a stable
contract for input/output per input tick.

## Input Tick Rate

Bots receive a snapshot once per input tick (default 30 Hz). This keeps gameplay
deterministic and matches the input clock. Faster rates are possible but should
be opt-in and tested for performance and fairness.

## Action Model

Bots return a simple action state that mirrors existing controller flags. An
optional `desired_turret_angle` lets bots request an absolute turret angle (in
radians) for smoother aiming. If provided, it overrides discrete turret flags.

## In-Process Python Bot API

### Interface

```python
class Bot:
    def update(self, state: "BotState") -> "BotAction":
        """Compute next action based on current state."""
```

### BotState (Python)

```python
@dataclass(frozen=True)
class BotState:
    tick_id: int
    dt: float
    self_state: "SelfState"
    visible_entities: list["VisibleEntity"]
    radar_hits: list["RadarHit"]
    fog_memory: "FogMemorySummary | None"
    map_bounds: "MapBounds"
    tile_size: int

@dataclass(frozen=True)
class SelfState:
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
    entity_id: int
    kind: str  # "tank", "mine", "bullet", "obstacle"
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
    entity_id: int
    kind: str  # "tank", "mine"
    distance: float
    bearing: float

@dataclass(frozen=True)
class FogMemorySummary:
    revealed_bounds: list[tuple[int, int, int, int]]  # (x, y, w, h) in fog tiles

@dataclass(frozen=True)
class MapBounds:
    width: int
    height: int
```

### BotAction (Python)

```python
@dataclass(frozen=True)
class BotAction:
    move_forward: bool = False
    move_backward: bool = False
    turn_left: bool = False
    turn_right: bool = False
    turret_left: bool = False
    turret_right: bool = False
    shoot: bool = False
    desired_turret_angle: float | None = None  # radians
```

## External Bot Protocol (JSON)

External bots communicate over stdin/stdout with one JSON request per tick.
Each request must receive one response. The engine provides a `tick_id` for
ordering. The bot should reply with the same `tick_id`.

### Request Schema (Engine -> Bot)

```json
{
  "type": "state",
  "tick_id": 1234,
  "dt": 0.0333333333,
  "self": {
    "id": 7,
    "x": 512.0,
    "y": 384.0,
    "rotation": 1.57,
    "turret_rotation": 2.10,
    "speed": 120.0,
    "hp": 100,
    "shoot_cooldown": 0.0,
    "team": 1
  },
  "visible_entities": [
    {
      "id": 12,
      "kind": "tank",
      "x": 640.0,
      "y": 320.0,
      "rotation": 0.80,
      "turret_rotation": 1.10,
      "team": 2,
      "active": true,
      "distance": 142.0,
      "bearing": -0.32
    }
  ],
  "radar_hits": [
    {
      "id": 21,
      "kind": "tank",
      "distance": 420.0,
      "bearing": 0.20
    }
  ],
  "fog_memory": {
    "revealed_bounds": [
      [4, 3, 6, 2],
      [12, 8, 3, 1]
    ]
  },
  "map_bounds": {
    "width": 1280,
    "height": 704
  },
  "tile_size": 64
}
```

### Response Schema (Bot -> Engine)

```json
{
  "type": "action",
  "tick_id": 1234,
  "move_forward": false,
  "move_backward": false,
  "turn_left": true,
  "turn_right": false,
  "turret_left": false,
  "turret_right": false,
  "shoot": true,
  "desired_turret_angle": 1.70
}
```

## Timing and Budgeting

- Bots should respond within a small per-tick budget (target 1-3 ms for
  in-process Python, 3-8 ms for external bots). The engine should enforce a
  timeout and reuse the last action or default to no-op if the bot is late.
- Input tick rate is 30 Hz by default; 60 Hz is possible but should be tested
  for CPU overhead, determinism, and multi-bot scaling.

## Notes

- If `desired_turret_angle` is present, it overrides `turret_left/right`.
- All angles are radians; `bearing` is relative to tank forward direction.
- Entity IDs are stable for the duration of a match.
