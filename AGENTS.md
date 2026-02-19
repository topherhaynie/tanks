# AI Assistant Guide

This document provides context and guidelines for AI coding assistants working on this project.

## Project Overview

**Tanks** is a 2D top-down tank battle game with:
- Realistic ricochet physics
- Human + bot playable
- Fog of war / limited vision for bots
- Tournament/training modes for AI development

**Current Phase:** Phase 3 (Bot Framework) - **COMPLETE**  
**Next Phase:** Phase 4 (External Bots & Game Modes) - C++ bot runner, tournament mode, metrics

See [docs/PROGRESS.md](docs/PROGRESS.md) for detailed status.

## Quick Start

1. **Project Structure:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system overview
2. **Code Style:** See [docs/CODING_STYLE.md](docs/CODING_STYLE.md) for syntax rules
3. **Design Docs:** See `docs/Project Plans/` for detailed specifications
4. **Run Game:** `python -m tanks` (requires Python 3.12+, pygame 2.6+)

## Key Concepts

### Dual-Clock Architecture
```python
INPUT_RATE = 30    # Hz - Deterministic input sampling for replay/networking
PHYSICS_RATE = 120 # Hz - High-accuracy collision detection
FPS = 60           # Rendering framerate
```

The game loop runs separate clocks for input and physics:
- **Input clock (30Hz):** Polls keyboard/mouse at fixed rate
- **Physics clock (120Hz):** Updates positions, checks collisions
- **Render (60fps):** Independent visual output

**Why:** Input determinism + collision accuracy without coupling.

### Swept Collision Detection
Bullets use continuous collision detection to prevent tunneling:
- Store `prev_x`, `prev_y` before moving
- Check line-line intersection between (prev → current) and wall edges
- Calculate time of impact to find earliest collision
- Fallback to circle-line check for robustness

**Critical:** Always check `entity.active` before collision processing.

### Entity Lifecycle
All entities (tanks, bullets) inherit from `Entity`:
- `active=True` when alive
- `active=False` when destroyed
- Renderer and collision system skip inactive entities

## Code Style Enforcements

### Type Annotations
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tanks.game.map import Map  # Avoid circular imports

def example(x: int, y: float = 0.0) -> tuple[int, float]:
    """Functions need full type coverage."""
    return (x + 1, y * 2)
```

### Google-Style Docstrings
```python
def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points.

    Args:
        x1: X coordinate of first point.
        y1: Y coordinate of first point.
        x2: X coordinate of second point.
        y2: Y coordinate of second point.

    Returns:
        The Euclidean distance between the points.
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
```

**Note:** Must include blank line before `Args:` and `Returns:`.

### Absolute Imports
```python
# ✅ CORRECT
from tanks.physics.vector import Vector
from tanks.entities.tank import Tank

# ❌ WRONG
from .vector import Vector
from ..entities.tank import Tank
```

### Ruff Configuration
The project uses Ruff for linting with these **intentional ignores**:
```toml
# ruff.toml
[lint]
ignore = [
    "PLR0913",  # Too many arguments - OK for game systems
    "FBT001",   # Boolean positional args - OK for simple flags
    "FBT002",   # Boolean default args - OK for toggles
    "FBT003",   # Boolean positional value - OK for clarity
    "ANN401",   # Any type allowed - OK for flexibility
]

[lint.mccabe]
max-complexity = 15  # Collision detection can be complex
```

**Don't:** Add more ignores without discussion.  
**Do:** Refactor if hitting complexity limits elsewhere.

## Common Patterns

### Adding a New Entity
1. Inherit from `Entity` in `entities/your_entity.py`
2. Add to game state in `core/game.py`
3. Add collision checks in `physics/collision.py`
4. Add rendering in `rendering/renderer.py`
5. Update type annotations everywhere

### Adding a Controller
1. Inherit from `Controller` in `input/controller.py`
2. Implement `update(dt)` method
3. Set tank action flags (move_forward, turn_left, shoot, etc.)
4. Add to demo mode or game mode

### Adding a Visual Effect
1. Inherit from `VisualEffect` in `effects/visual.py`
2. Implement `update(dt)` and `is_finished()` methods
3. Add creation in appropriate game event
4. Add rendering in `renderer.render_effects()`

## Important Files

### Phase 2 - Completed (Perception)
- `src/tanks/perception/vision.py` - Vision raycasting and radar detection
### Phase 2 - Completed (Perception)
- `src/tanks/perception/vision.py` - Vision raycasting and radar detection
- `src/tanks/perception/memory.py` - Terrain memory system  
- `src/tanks/rendering/renderer.py` - Fog of war rendering with gradients
- `src/tanks/core/game.py` - Perception update integration
- `src/tanks/entities/tank.py` - Tank vision state and fog memory

### Phase 3 - Completed (Bot Framework)
- `src/tanks/bots/bot_api.py` - Protocol and dataclasses
- `src/tanks/bots/sensors.py` - Sensor snapshot builder
- `src/tanks/bots/bot_controller.py` - Controller adapter for bots
- `src/tanks/bots/simple_bot.py` - Wander/seek bot with randomness
- `src/tanks/bots/smart_bot.py` - Radar pursuit bot with stuck detection
- `src/tanks/rendering/fog.py` - Tinted fog for observer mode
- `src/tanks/rendering/tanks.py` - Observer rendering with alpha
- `src/tanks/demo.py` - Bot demo modes
- `docs/Project Plans/06_Bot_API.md` - External bot protocol spec
- `docs/bot_api.schema.json` - JSON schema

### Critical for Phase 4 (External Bots & Game Modes)
- `src/tanks/bots/external_runner.py` - Process management for external bots
- `src/tanks/bots/cpp/` - C++ bot SDK and examples
- `src/tanks/modes/` - Tournament and arena modes
- `src/tanks/core/stats.py` - Performance metrics tracking
- `src/tanks/rendering/camera.py` - Camera system (follow and global views)
- `src/tanks/maps/generator.py` - Procedural map generation
- `src/tanks/maps/loader.py` - Enhanced map loading and validation

### Configuration
- `src/tanks/config/constants.py` - Tunable parameters (speeds, sizes, rates)
- `src/tanks/config/settings.py` - Runtime toggles (debug, pause)
- `ruff.toml` - Linter config (don't change ignores)
- `.vscode/settings.json` - IDE config for Ruff extension

### Core Systems
- `src/tanks/core/game.py` - Main loop with dual clocks
- `src/tanks/core/clock.py` - Fixed timestep accumulator
- `src/tanks/physics/collision.py` - Swept collision detection
- `src/tanks/entities/bullet.py` - Bullet with prev position tracking

## Common Tasks

### "Make bullets faster"
1. Edit `BULLET_SPEED` in `config/constants.py`
2. Test at high speeds to ensure no tunneling
3. If tunneling occurs, increase `PHYSICS_RATE` (currently 120Hz)

### "Add a new tank parameter"
1. Add constant in `config/constants.py`
2. Use in `entities/tank.py`
3. Consider if it needs UI display in `rendering/renderer.py`

### "Fix a collision bug"
1. Check if entities have `active=True` check
2. Verify swept collision is checking full path
3. Test with debug hitboxes: set `settings.SHOW_HITBOXES = True`
4. Check if `prev_x`, `prev_y` are updated before movement

### "Add a sound effect"
1. Add placeholder in `audio/__init__.py` SoundManager
2. Call `game.sound_manager.play(sound_name, position)` at event
3. (Future) Add actual sound file loading

## Testing

Currently minimal automated testing. When adding tests:
- Place in `tests/` directory
- Mirror source structure (e.g., `tests/physics/test_collision.py`)
- Use pytest conventions
- Mock pygame dependencies

## Phase-Specific Guidance

### Phase 1 (Complete) ✅
Core engine is stable. Don't heavily refactor unless necessary.

### Phase 2 (Complete) ✅
Perception system is complete and performant. Key achievements:
- Vision raycasting with 200px radius
- Fog of war with 32px tiles and smooth gradients
- Terrain memory system
- Radar detection (600px radius, through-wall)
- 60 FPS maintained with full fog effects

### Phase 3 (Complete) ✅
Bot framework is stable. Key achievements:
- Python bot API with dataclasses (BotState, BotAction)
- Sensor snapshot system (vision, radar, fog memory)
- BotController integration with input system
- SimpleBot and SmartBot implementations
- Observer rendering with dual fog overlays
- Bot-vs-bot demo with global view
- External bot protocol documented (JSON schema)

Implemented files:
- `src/tanks/bots/bot_api.py` - Protocol definitions
- `src/tanks/bots/sensors.py` - State snapshot builder
- `src/tanks/bots/bot_controller.py` - Controller adapter
- `src/tanks/bots/simple_bot.py` - Basic bot
- `src/tanks/bots/smart_bot.py` - Advanced bot
- `src/tanks/rendering/fog.py` - Tinted fog rendering
- `src/tanks/rendering/tanks.py` - Observer tank rendering

### Phase 4 (Next - External Bots & Game Modes)
Focus areas:
- `src/tanks/bots/external_runner.py` - Subprocess management for C++/other bots
- `src/tanks/bots/cpp/` - C++ SDK with headers and examples
- `src/tanks/modes/tournament.py` - Tournament framework
- `src/tanks/core/stats.py` - Performance metrics (kills, deaths, accuracy)
- `src/tanks/rendering/camera.py` - Camera system (follow and global views)
- `src/tanks/maps/generator.py` - Procedural map generation
- `src/tanks/maps/loader.py` - Enhanced map loading and validation
- External bot timeout handling and watchdog
- Camera modes: follow tank (single-player) and global view (observer/training)
- Large map support with smooth scrolling

## Debugging Tips

### Physics Issues
- Enable debug rendering: `settings.SHOW_HITBOXES = True`
- Check `PHYSICS_RATE` is 120Hz
- Verify swept collision is enabled
- Print collision normals and velocities

### Performance Issues
- Profile with `cProfile`
- Check if too many entities active
- Verify spatial optimization in collision detection
- Consider entity pooling for bullets

### Input Lag
- Check `INPUT_RATE` is 30Hz (not too high)
- Verify controller `update()` is called from input clock
- Don't poll input in physics loop

## Anti-Patterns to Avoid

❌ **Polling input in physics loop** - Use input clock only  
❌ **Discrete collision only** - Always use swept for fast-moving objects  
❌ **Forgetting `active` checks** - Dead entities must be ignored  
❌ **Relative imports** - Use absolute imports everywhere  
❌ **Magic numbers** - Add constants to `constants.py`  
❌ **Mixing clocks** - Keep input/physics/render concerns separate  
❌ **Global state** - Pass through game state objects  
❌ **Ignoring type errors** - Fix them, don't suppress  

## Getting Help

1. **Design Questions:** Read `docs/Project Plans/` first
2. **Code Style:** Check `docs/CODING_STYLE.md`
3. **Architecture:** See `docs/ARCHITECTURE.md`
4. **Progress:** Review `docs/PROGRESS.md`
5. **Task List:** Check current phase in `docs/Project Plans/05_Roadmap.md`

## Contribution Guidelines (for AI Agents)

1. **Always read before writing:** Use grep/semantic search to understand context
2. **Type everything:** Add type annotations to all new code
3. **Document as you go:** Google-style docstrings for public APIs
4. **Test collision changes:** Sweep collision is critical, don't break it
5. **Respect the clocks:** Don't mix input/physics/render concerns
6. **Check your work:** Run `ruff check .` before finishing
7. **Update docs:** If architecture changes, update ARCHITECTURE.md

## Quick Reference

### Important Constants
```python
PHYSICS_RATE = 120        # Physics updates per second
INPUT_RATE = 30           # Input sampling rate
FPS = 60                  # Rendering framerate
TILE_SIZE = 32           # Map tile size in pixels
TANK_RADIUS = 16         # Tank collision radius
BULLET_RADIUS = 3        # Bullet collision radius
BULLET_SPEED = 400       # Bullet speed (pixels/second)
TANK_HP = 100            # Tank starting HP
BULLET_DAMAGE = 25       # Damage per hit
MAX_BOUNCES = 3          # Bullet bounces before expiring
```

### Key Files by Task
- **Add gameplay feature:** `core/game.py`, `entities/`
- **Tune parameters:** `config/constants.py`
- **Fix collision:** `physics/collision.py`
- **Change rendering:** `rendering/renderer.py`
- **Add input method:** `input/keyboard.py` or new controller
- **Add bot AI:** `bots/` (Phase 4)
- **Add perception:** `perception/` (Phase 2)

---

**Remember:** This is a learning project for AI bot development. The goal is clean, understandable code that others can learn from. Prefer clarity over cleverness.
