# Project Architecture

## Directory Structure

```
tanks/
├── src/tanks/              # Main source code
│   ├── __main__.py        # Entry point with game mode selection
│   ├── demo.py            # Two-player demo mode
│   │
│   ├── audio/             # Sound system
│   │   └── __init__.py    # SoundManager with placeholder hooks
│   │
│   ├── bots/              # Bot framework (Phase 4)
│   │   └── __init__.py
│   │
│   ├── config/            # Game configuration
│   │   ├── constants.py   # Tunable gameplay parameters
│   │   └── settings.py    # Runtime settings (debug, pause, etc.)
│   │
│   ├── core/              # Core game systems
│   │   ├── clock.py       # Fixed timestep clock (dual-rate)
│   │   ├── events.py      # Event system
│   │   └── game.py        # Main game class and loop
│   │
│   ├── effects/           # Visual effects
│   │   └── visual.py      # MuzzleFlash, VisualEffect base class
│   │
│   ├── entities/          # Game objects
│   │   ├── entity.py      # Base Entity class
│   │   ├── tank.py        # Tank with HP, shooting, movement
│   │   ├── bullet.py      # Bullet with ricochet and lifetime
│   │   ├── mine.py        # (Future) Mine entity
│   │   └── obstacle.py    # (Future) Destructible obstacles
│   │
│   ├── input/             # Input handling
│   │   ├── controller.py  # Base Controller class
│   │   └── keyboard.py    # KeyboardController, KeyboardController2
│   │
│   ├── maps/              # Map system
│   │   ├── map.py         # Map class with tiles and spawn points
│   │   └── loader.py      # MapLoader with arena generator
│   │
│   ├── modes/             # Game modes (Phase 5)
│   │   └── __init__.py
│   │
│   ├── perception/        # Perception systems (Phase 2)
│   │   └── __init__.py
│   │
│   ├── physics/           # Physics systems
│   │   ├── vector.py      # 2D Vector class
│   │   ├── movement.py    # MovementSystem (tank/turret movement)
│   │   ├── projectile.py  # ProjectileSystem (ricochet)
│   │   └── collision.py   # CollisionSystem (swept collision)
│   │
│   ├── rendering/         # Rendering systems
│   │   ├── renderer.py    # Main Renderer class
│   │   ├── camera.py      # (Future) Camera system
│   │   ├── debug.py       # (Future) Debug visualization
│   │   ├── sprites.py     # (Future) Sprite system
│   │   └── layers.py      # (Future) Rendering layers
│   │
│   └── utils/             # Utility functions
│       ├── geometry.py    # Collision detection helpers
│       └── math_utils.py  # Math utilities (clamp, lerp, angles)
│
├── tests/                 # Test suite
│
├── docs/                  # Documentation
│   ├── Project Plans/     # Design documents
│   │   ├── 01_Project_Overview.md
│   │   ├── 02_Physics_and_Movement.md
│   │   ├── 03_Sensors_and_Fog.md
│   │   ├── 04_Game_Architecture.md
│   │   └── 05_Roadmap.md
│   ├── PROGRESS.md        # Current progress checklist
│   ├── ARCHITECTURE.md    # This file
│   └── CODING_STYLE.md    # Code style guide
│
├── assets/                # Game assets (future)
│   └── sounds/            # Sound files (when added)
│
├── ruff.toml              # Ruff linter configuration
├── pyproject.toml         # Python project metadata
├── README.md              # Project readme
├── AGENTS.md              # AI assistant guidance
└── LICENSE                # MIT License
```

## System Architecture

### Game Loop (core/game.py)

The game uses a **dual-clock architecture** for optimal performance and determinism:

```
Main Loop (60 FPS rendering)
├── Input Clock @ 30Hz  → update_input()   # Deterministic input sampling
├── Physics Clock @ 120Hz → update_physics() # High-accuracy collision
└── Render @ 60 FPS     → render_frame()    # Visual output
```

**Benefits:**
- Input sampled at fixed rate for replay/networking
- Physics runs 4x faster than input for accurate collision
- Rendering independent of simulation rate

### Entity System

All game objects inherit from `Entity` base class:
- Unique ID assignment
- Position (x, y)
- Active flag for lifecycle management

**Entity Hierarchy:**
```
Entity (entities/entity.py)
├── Tank (entities/tank.py)
│   ├── HP and damage
│   ├── Shooting cooldown
│   ├── Team assignment
│   └── Body + turret rotation
│
└── Bullet (entities/bullet.py)
    ├── Velocity tracking
    ├── Previous position (for swept collision)
    ├── Bounce counter
    └── Lifetime timer
```

### Physics Systems

**CollisionSystem (physics/collision.py)**
- Swept collision for bullets (continuous collision detection)
- Circle-circle, circle-line, line-line intersection
- Active entity checks
- Tile-based spatial optimization

**MovementSystem (physics/movement.py)**
- Tank body movement with rotation
- Turret aiming (mouse or keyboard)
- Movement constraints

**ProjectileSystem (physics/projectile.py)**
- Bullet bouncing with reflection
- Bounce limit enforcement

### Rendering Pipeline

**Layers (bottom to top):**
1. Background color
2. Map tiles (walls)
3. Bullets
4. Tanks (body + turret + HP bar)
5. Visual effects (muzzle flash)
6. Debug overlays (hitboxes, FPS)

### Input System

**Controller Pattern:**
- Base `Controller` class with `update(dt)` method
- `KeyboardController` for player 1 (WASD + mouse)
- `KeyboardController2` for player 2 (arrows + JL keys)
- Future: `BotController` for AI agents

### Configuration System

**constants.py** - Immutable game parameters:
- Display settings (window size, FPS)
- Physics rates (INPUT_RATE=30, PHYSICS_RATE=120)
- Tile sizes
- Tank parameters (speed, turn rate, HP)
- Bullet parameters (speed, damage, lifetime, bounces)

**settings.py** - Runtime toggles:
- Debug overlays
- Hitbox display
- Pause state
- FPS counter

## Key Design Decisions

### 1. Dual-Clock Architecture
**Why:** Separate input sampling (30Hz) from physics updates (120Hz)
- Input rate kept low for determinism and potential networking
- Physics rate high for collision accuracy
- Prevents bullet tunneling even at high speeds

### 2. Swept Collision Detection
**Why:** Bullets can move 3.33 pixels per physics frame
- Line-line intersection between bullet path and walls
- Catches collisions between discrete positions
- Eliminates tunneling completely

### 3. Active Flag Pattern
**Why:** Simple lifecycle management
- Destroyed entities set `active=False`
- Renderer skips inactive entities
- Collision system skips inactive entities
- Easy cleanup in game loop

### 4. Type Annotations + Docstrings
**Why:** Code quality and maintainability
- 100% type coverage for IDE support
- Google-style docstrings for clear documentation
- Ruff linting for consistency

### 5. Absolute Imports
**Why:** Clarity and refactoring safety
- `from tanks.physics.vector import Vector`
- Easy to understand import paths
- IDE navigation works perfectly

## Data Flow

### Shooting Flow
```
Player Input → KeyboardController.update()
    ↓
Game.shoot_bullet(tank)
    ↓
Create Bullet entity
    ├→ Add to game.state.bullets
    ├→ Create MuzzleFlash effect
    └→ Play shoot sound
    ↓
Physics Update
    ├→ Bullet.update() - move bullet
    ├→ CollisionSystem.check_bullet_wall_collision()
    │   ├→ Swept collision check
    │   └→ If hit: ProjectileSystem.bounce_bullet()
    └→ CollisionSystem.check_bullet_tank_collision()
        └→ If hit: Tank.take_damage()
    ↓
Render
    └→ Renderer.render_bullets()
```

### Collision Detection Flow
```
Bullet Position Update
    ↓
Get nearby tiles (spatial optimization)
    ↓
For each tile edge:
    ├→ Check swept collision (line-line)
    │   └→ Calculate time of impact
    └→ Check circle collision (current position)
    ↓
Select earliest collision (swept has priority)
    ↓
Calculate surface normal
    ↓
Check if approaching (velocity · normal < 0)
    ↓
Return closest valid collision
```

## Extension Points (for Phase 2+)

### Vision System (Phase 2)
- Add `tanks/perception/vision.py`
- Raycasting from tank position
- Integrate with renderer for fog overlay

### Bot API (Phase 4)
- Add `tanks/bots/bot_controller.py`
- Sensor API in `tanks/perception/sensors.py`
- Bot action interface (move, turn, shoot)

### Map Editor (Phase 5)
- Add `tanks/tools/map_editor.py`
- Visual tile placement
- Export to JSON format

### Networking (Future)
- Deterministic input replay
- 30Hz input rate makes this feasible
- Lockstep or rollback netcode
