# Phase 1 Progress - Core Engine

**Status**: ✅ COMPLETE

## Completed Features

### Core Systems
- [x] Pygame window and rendering pipeline
- [x] Fixed timestep physics (120Hz)
- [x] Input polling (30Hz for determinism)
- [x] Event system
- [x] Game loop with separate input/physics/render stages

### Tank Movement
- [x] Smooth circular tank movement
- [x] Tank body rotation
- [x] Independent turret rotation
- [x] Collision with walls (sliding)
- [x] Tank-to-tank collision
- [x] Movement parameters (speed, turn rate, turret rate)

### Shooting & Projectiles
- [x] Bullet firing system
- [x] Shoot cooldown
- [x] Bullet ricochet (single bounce max)
- [x] Bullet lifetime
- [x] Continuous collision detection (no tunneling)
- [x] Swept collision for fast bullets

### Collision System
- [x] Circle-circle collision
- [x] Circle-line collision
- [x] Line-line intersection
- [x] Tile-based wall collision
- [x] Multiple wall types (solid, horizontal, vertical, diagonal)
- [x] Proper normal calculation
- [x] Active entity checks (ignore destroyed tanks)

### Damage & Combat
- [x] HP system
- [x] Bullet damage
- [x] Tank destruction
- [x] Team system (friendly fire prevention)
- [x] HP bar rendering

### Maps
- [x] Tile-based map system (64x64 tiles)
- [x] Simple arena generator
- [x] Spawn points with team assignment
- [x] Map loader foundation (JSON ready)

### Visual Effects
- [x] Muzzle flash on shooting
- [x] Visual effect system with alpha fading
- [x] Star-shaped flash rendering

### Audio System
- [x] Sound manager with placeholder system
- [x] Shoot sound hook
- [x] Hit sound hook
- [x] Bounce sound hook
- [x] Graceful fallback if pygame.mixer unavailable

### UI & Controls
- [x] Two-player keyboard support
  - Player 1: WASD + Mouse aim + Space shoot
  - Player 2: Arrow keys + J/L aim + RCtrl shoot
- [x] Game mode selection menu
- [x] FPS/TPS display
- [x] Debug overlays (F1, F2)
- [x] Pause (P)
- [x] Proper window close handling

### Code Quality
- [x] Type annotations (100% coverage)
- [x] Google-style docstrings
- [x] Ruff linting configuration
- [x] Coding style guide documentation
- [x] Absolute imports throughout

## Phase 1 Refinements Completed
- [x] Dual-clock system (input @ 30Hz, physics @ 120Hz)
- [x] Visual effects (muzzle flash)
- [x] Sound system placeholders
- [x] Two-player demo mode
- [x] Improved collision accuracy (swept collision)
- [x] Menu system with mode selection

## Known Issues
None currently identified.

## Phase 1 Review
All objectives met. System is stable with:
- No tunneling
- Accurate collision detection
- Smooth gameplay at 60 FPS
- Deterministic physics at 120Hz
- Clean code with full type coverage

---

# Phase 2 Progress - Perception System

**Status**: ✅ COMPLETE

## Completed Features

### Vision System
- [x] 200px vision radius with line-of-sight raycasting
- [x] DDA algorithm for efficient wall detection
- [x] Quarter-tile step precision (TILE_SIZE/4)
- [x] Walls reveal themselves when encountered
- [x] Incremental fog revelation along raycast path

### Fog of War
- [x] 32px fog tiles (half of 64px game tiles for detail)
- [x] Two-pass rendering system (solid fog + gradient edges)
- [x] Pre-rendered gradient stamp for performance
- [x] Smooth circular gradients with 20-step blending
- [x] 2x FOG_TILE_SIZE radius gradient stamps
- [x] Exponential alpha falloff for natural appearance
- [x] Entity visibility filtering based on vision/fog
- [x] Maintains 60 FPS with full fog effects

### Terrain Memory
- [x] Per-tank fog memory system
- [x] Grid-based boolean array (40x22 fog tiles for 20x11 map)
- [x] Persistent terrain discovery
- [x] Revealed tiles stay visible even when out of vision range
- [x] Memory-based entity visibility (entities in discovered areas visible)

### Radar System
- [x] 600px radar radius (through-wall detection)
- [x] Detects tanks and mines only (ignores bullets/obstacles)
- [x] Team-based filtering (doesn't detect teammates)
- [x] Pulsing radar blip visualization
- [x] Radar blips rendered on top of fog layer
- [x] Distance-based radar blip rendering

### Debug Controls
- [x] F3: Toggle fog of war
- [x] F4: Toggle perspective tank (switch fog viewpoint)
- [x] Existing F1/F2 debug overlays work with perception

### Code Quality
- [x] Type annotations throughout perception system
- [x] Google-style docstrings
- [x] Passes Ruff linting
- [x] Organized into perception/ module

## Phase 2 Implementation Details

### Performance Optimization
- Used pre-rendered gradient stamp (created once at init)
- Only apply gradients at fog edges (_has_fog_neighbor check)
- Fog tile size = 32px for detail without overhead
- Efficient raycasting with early wall detection

### Visual Quality Decisions
- Larger gradient stamps (2x vs 1.5x FOG_TILE_SIZE) for smoother blending
- Exponential alpha falloff (progress^1.5) for natural fog appearance
- Reveal all fog tiles along raycast path for consistent directional behavior
- Reveal wall tiles AND adjacent tiles for proper wall surface visibility

## Known Issues
None currently identified.

## Future Enhancements
- [ ] **Radar Enhancement**: Replace current pulsing circles with realistic rotating radar beam effect:
  - Green rotating beam emanating from tank
  - Faded afterimage trail as beam rotates
  - Temporary blips at last known entity locations (fade over time)
  - More authentic radar sweep appearance
- [ ] **Line of Sight Precision**: Treat targets as circles and allow visibility when any part of the target is visible (not just center-to-center).

## Phase 2 Review
All objectives met. Perception system is stable with:
- Smooth fog of war with natural appearance
- Accurate line-of-sight vision
- Performant rendering (60 FPS maintained)
- Incremental terrain discovery
- Through-wall radar detection
- Clean separation of vision and radar systems

---

# Phase 3 Progress - Bot Framework

**Status**: ✅ COMPLETE

## Completed Features

### Bot Infrastructure
- [x] Bot controller base class (BotController integrates with input system)
- [x] Sensor API (sensors.py builds comprehensive bot state snapshots)
- [x] Python bot API with dataclasses (Protocol, BotState, BotAction, etc.)
- [x] bot_api.py with full type annotations
- [x] JSON schema for external bot protocol (bot_api.schema.json)
- [x] Bot API documentation (06_Bot_API.md)

### Bot Implementations
- [x] SimpleBot with randomized wander/seek behavior
- [x] SmartBot with radar pursuit and stuck detection
- [x] Both bots use perception system (vision, radar, fog memory)

### Observer Rendering
- [x] Global perspective mode for watching bot matches
- [x] Dual fog overlay system with RGB tinting
- [x] Semi-transparent hidden tanks (70% alpha)
- [x] Configurable fog opacity (50% default)
- [x] Observer rendering pipeline with fog color customization

### Demo Modes
- [x] Two-player keyboard demo
- [x] Player vs Bot demo (human vs SimpleBot)
- [x] Bot vs Bot demo with global observer view
- [x] Corner spawn positioning for bot battles
- [x] Menu integration for all modes

### Code Quality
- [x] Full type annotations throughout bot system
- [x] Google-style docstrings
- [x] Passes Ruff linting
- [x] Named constants for tunable parameters
- [x] Organized into bots/ module

## Phase 3 Implementation Details

### Bot State Snapshot
- Self state: position, rotation, HP, cooldown, team
- Visible entities: tanks, bullets, obstacles with distance/bearing
- Radar hits: through-wall detection with distance/bearing
- Fog memory summary: run-length encoded revealed bounds
- Map bounds and tile size

### Bot Action Model
- Boolean flags for movement (forward/backward, turn left/right)
- Boolean flags for turret and shooting
- Optional desired_turret_angle for smooth aiming override
- 30Hz update rate matching input clock

### Observer View Features
- Renders all entities from god's-eye perspective
- Shows both bots' individual fog of war simultaneously
- Color-codes fog per bot (blue/red by default)
- Adjustable opacity for fog overlays
- Hidden tanks rendered with reduced alpha when not visible to enemy

## Known Issues
None currently identified.

## Future Enhancements
- [ ] **Line-of-sight precision**: Treat targets as circles (center-to-edge visibility)

## Phase 3 Review
All core objectives met. Bot framework is production-ready with:
- Clean Python bot API with type safety
- Comprehensive sensor snapshot system
- Two working bot implementations
- Observer mode for watching bot matches
- Full integration with perception system
- Documented external bot protocol (implementation deferred to Phase 4)

---

# Phase 4 Progress - External Bots and Game Modes

**Status**: 🚧 IN PROGRESS

## Completed Features

### External Bot Infrastructure
- [x] External bot runner (subprocess management and JSON IPC)
- [x] Bot timeout enforcement and watchdog system
- [x] External bot controller (Controller interface wrapper)
- [x] Error recovery (crash detection, restart logic)
- [x] Statistics tracking (tick count, timeouts, errors)
- [x] Automated testing with mock external bot
- [x] Field name translation (entity_id → id for external protocol)
- [x] Proper JSON serialization/deserialization

### C++ Bot SDK
- [x] Core headers (tanks_bot.h with all data structures)
- [x] JSON bridge (tanks_json_bridge.h with parsing/serialization)
- [x] Bot main loop helper (run_bot_loop utility)
- [x] Example bot implementation (simple_bot.cpp with wander/seek)
- [x] CMake build system (with automatic nlohmann/json fetching)
- [x] Complete SDK documentation (README with examples)
- [x] BUILD guide for C++ bot developers

### Integration & Testing
- [x] Full C++ bot integration test (Python ↔ C++ ↔ Python)
- [x] Wander behavior verification
- [x] Seek behavior verification (enemy detection and targeting)
- [x] Performance test (100 ticks under 8ms budget)
- [x] Subprocess lifecycle management verified
- [x] Zero timeouts in production conditions
- [x] Mixed bot battle demo (C++ + Python bots competing)

### Demo Modes
- [x] Two-player keyboard demo
- [x] Player vs bot demo
- [x] Bot vs bot demo (global observer view)
- [x] Mixed bot battle (3-way: C++ + SimpleBot + SmartBot)

### Code Quality
- [x] Full type annotations throughout
- [x] Google-style docstrings
- [x] Passes Ruff linting
- [x] Integration with existing bot system
- [x] Organized into bots/ module

### Bot Performance Metrics (NEW)
- [x] StatsTracker system for tracking all match statistics
- [x] Per-tank stats: kills, deaths, accuracy, damage dealt/taken
- [x] Survival time and distance traveled tracking
- [x] Live stats overlay (F6 toggle)
- [x] Post-match statistics summary
- [x] Leaderboard sorting (by kills, accuracy, damage, K/D ratio)
- [x] Team-level aggregated statistics
- [x] Integration with all demo modes

### Camera System (NEW)
- [x] Enhanced Camera class with multiple modes
- [x] GLOBAL mode: shows entire map with auto-zoom
- [x] FOLLOW mode: smooth camera tracking of selected tank
- [x] FREE mode: manual pan with arrow keys and zoom with +/-
- [x] Viewport culling for efficient rendering
- [x] Camera controls: C=cycle mode, Tab=switch target, +/-=zoom
- [x] Integration with all renderers (map, tanks, bullets)
- [x] Coordinate transforms (world to screen, screen to world)
- [x] Map boundary clamping with smart centering
- [x] Zoom scaling for all visual elements
- [x] Arrow keys for panning in FREE mode
- [x] Viewport culling for improved performance
- [x] Smooth camera interpolation (follow mode)
- [x] Map boundary clamping
- [x] World-to-screen coordinate transforms with zoom
- [x] Integration with all renderers (map, tanks, bullets)
- [x] Demo-specific camera defaults (FOLLOW for player, GLOBAL for bot battles)

## Phase 4 Implementation Details

### External Bot Runner
- Uses subprocess.Popen for process management
- JSON communication over stdin/stdout
- 8ms timeout per tick (configurable)
- Fallback to last action on timeout
- Automatic restart after 3 consecutive errors
- Statistics tracking for monitoring

### C++ SDK Architecture
- Header-only design for easy integration
- Uses nlohmann/json for JSON parsing
- Abstract TankBot base class
- Complete protocol implementation matching 06_Bot_API.md
- Example bot with realistic seek/wander behavior

### Testing
- Mock bot test validates JSON IPC pipeline
- Subprocess management tested
- Timeout and error handling verified
- Ready for C++ bot integration when CMake available

### Camera System
- Enhanced Camera class with multiple modes
- GLOBAL mode: shows entire map with auto-zoom
- FOLLOW mode: smooth camera tracking of selected tank
- FREE mode: manual pan with arrow keys and zoom with +/-
- Viewport culling for efficient rendering on large maps
- Camera controls: C=cycle mode, Tab=switch target, +/-=zoom
- Integration with all renderers (map, tanks, bullets)
- Coordinate transforms (world to screen, screen to world)
- Map boundary clamping with smart centering
- Zoom scaling for all visual elements

### Observer Fog Rendering
- Fixed fog colors for global observer mode
- Transparent gray fog (30% opacity) for undiscovered areas
- Colored fog overlays (40% opacity) for team-discovered areas
- Additive color blending where multiple tanks explore
- Proper fog gradients at edges
- Three-layer rendering system for clarity

### Procedural Map Generator
- MapGenerator class with configurable parameters
- Multiple map sizes: SMALL (20x11), MEDIUM (40x22), LARGE (60x34), HUGE (80x45)
- Six terrain patterns:
  - OPEN_ARENA: minimal obstacles for open combat
  - SCATTERED: random obstacle distribution
  - MAZE: recursive division algorithm with gaps
  - ROOMS: connected rectangular rooms
  - CORRIDORS: horizontal/vertical passage network
  - FORTRESS: central keep with defensive walls
- Obstacle density control (0-1 fraction)
- Border wall generation
- Symmetric map support for competitive fairness
- Balanced spawn point generation (2-4+ spawns)
- Map validation with flood-fill reachability checks
- Configurable random seed for reproducibility
- Cover cluster placement for tactical positioning

## In Progress Features
- [x] Demo mode with external bot integration (3-way battle: C++, SimpleBot, SmartBot)
- [x] Controller interface compliance (ExternalBotController matches base Controller)
- [x] Bot performance metrics (kills, deaths, accuracy, damage, survival time, distance traveled)
- [x] Camera system for larger maps (follow + global modes)
- [x] Observer fog rendering improvements (proper color mixing)
- [x] Procedural map generator (multiple sizes and patterns)
- [x] Tournament mode framework (scheduling, ranking, leaderboards)
- [x] Arena mode (4-8 tank multi-tank battles)

### Tournament Mode Framework
- [x] Win conditions: Last alive, time limit (most kills), elimination target
- [x] Match management: Match data, results, points calculation
- [x] Tournament formats: Round-robin, single elimination, ladder
- [x] Leaderboard system: Rankings by points, K/D ratio, kill counts
- [x] Match scheduling and progression
- [x] Tournament statistics aggregation

### Arena Mode
- [x] Arena size configurations: Skirmish, Standard, Large, Chaos
- [x] Multi-tank spawning (3-8 tanks simultaneously)
- [x] Procedural map generation integration
- [x] Bot controller assignment for each tank
- [x] Observer view with distinct fog colors per tank
- [x] Arena statistics and results tracking
- [x] Demo mode with difficulty selection

## Remaining Phase 4 Features
None - Phase 4 Complete! ✅

## Phase 4 Completion Summary

**All Phase 4 Features Implemented:**
- ✅ External bot runner with JSON IPC and timeout handling
- ✅ C++ bot SDK with example implementations
- ✅ Bot performance metrics system (kills, deaths, accuracy, etc.)
- ✅ Camera system with GLOBAL, FOLLOW, and FREE modes
- ✅ Observer fog rendering with proper color mixing
- ✅ Procedural map generator with 6 terrain patterns and 4 size presets
- ✅ Tournament mode framework with win conditions and leaderboards
- ✅ Arena mode (4-8 tank simultaneous battles)
- ✅ Line-of-sight precision enhancement (center-to-edge visibility)

**Vision System Enhancement: Center-to-Edge Raycasting**
- Fast path: Check ray from tank center to entity center
- Precision path: Test 8 rays to entity perimeter (N, NE, E, SE, S, SW, W, NW)
- Accurate circular visibility with obstacle wrapping
- Catches cases where entity center is blocked but edge is visible
- Works for all entity types (tanks, bullets, mines)

**5 Playable Game Modes:**
1. Two-Player Demo (local multiplayer with fog of war)
2. Player vs Bot (human vs AI with SmartBot)
3. Bot vs Bot (observer view with metrics)
4. Mixed Bot Battle (C++ + Python bots 3-way)
5. Arena Battle (4-8 bots, 4 difficulty levels)

---

## Known Issues
None currently identified.

---

# Phase 5 Progress - Expanded Weapon System

**Status**: ✅ COMPLETE

## Completed Features

### Missile Implementation
- [x] Missile entity class with swept collision detection
- [x] Fast projectiles (600 px/s = 1.5x bullet speed)
- [x] No ricochet - explode on first wall impact
- [x] Higher damage (2 vs 1 for bullets)
- [x] 3-second cooldown between shots
- [x] Collision with walls (immediate destruction)
- [x] Collision with tanks (apply damage)
- [x] Sensor integration (missiles visible to radar/vision)
- [x] Rendering (orange colored projectiles)

### Mine Implementation
- [x] Mine entity class with proximity trigger
- [x] Deployable at tank position (not fired)
- [x] 3-mine maximum capacity per tank
- [x] 5-second placement cooldown
- [x] 1-second arm delay (prevents triggering on placer)
- [x] Proximity trigger radius (40px)
- [x] Blast radius damage (60px) - hits all nearby tanks
- [x] Higher damage (3 vs 1 for bullets)
- [x] Trigger on tank proximity OR projectile impact
- [x] Sensor integration (mines visible to radar/vision)
- [x] Rendering (purple colored circles)

### Game System Integration
- [x] Game state tracks missiles and mines (GameState lists)
- [x] Physics updates for both projectile types
- [x] Collision detection (wall, tank, mine proximity)
- [x] Stats tracking integration (hits, kills with new weapons)
- [x] Perception system includes missiles/mines in entity lists
- [x] Mine blast radius damage to all enemy tanks in range

### Tank Weapon Management
- [x] Missile cooldown tracking (missile_cooldown)
- [x] Mine cooldown tracking (mine_cooldown)
- [x] Mine ammo counter (mine_count 0-3)
- [x] Tank methods: can_fire_missile(), fire_missile()
- [x] Tank methods: can_place_mine(), place_mine(), refill_mines()
- [x] Weapon state in tank update loop

### Bot API Extensions
- [x] BotState includes missile_cooldown, mine_cooldown, mine_count
- [x] BotAction includes fire_missile, place_mine flags
- [x] Sensor system detects missiles as "missile" kind
- [x] Sensor system detects mines as "mine" kind
- [x] Radar includes missiles and mines in radar_hits
- [x] Vision includes missiles and mines in visible_entities

### Gameplay Controls
- [x] Keyboard: M key for missile firing (Player 1: WASD+M)
- [x] Keyboard: N key for mine placement (Player 1: WASD+N)
- [x] Keyboard: Backslash (\) for missile (Player 2: Arrows+\)
- [x] Keyboard: Plus (=) for mine (Player 2: Arrows+=)
- [x] Bot controllers automatically handle new actions
- [x] External bot protocol supports new weapons

### UI Display
- [x] Weapon status HUD showing cooldowns and ammo
- [x] Bullet status: Ready/Cooldown duration
- [x] Missile status: Ready/Cooldown duration (cyan color)
- [x] Mine status: X/3 mines, Ready/Cooldown (magenta color)
- [x] Dynamic color coding (green=ready, gray=cooldown)
- [x] Integrated into existing HUD rendering pipeline
- [x] Displays below jamming status indicator

### Game Constants
- [x] MISSILE_SPEED = 600 px/s
- [x] MISSILE_RADIUS = 6 px
- [x] MISSILE_DAMAGE = 2
- [x] MISSILE_LIFETIME = 5.0 seconds
- [x] MISSILE_COOLDOWN = 3.0 seconds
- [x] MAX_MISSILES = 1 (one in flight per tank)
- [x] MINE_RADIUS = 8 px
- [x] MINE_BLAST_RADIUS = 60 px
- [x] MINE_DAMAGE = 3
- [x] MINE_PLACEMENT_COOLDOWN = 5.0 seconds
- [x] MINE_MAX_COUNT = 3
- [x] MINE_TRIGGER_RADIUS = 40 px
- [x] COLOR_MISSILE = (255, 100, 50) orange
- [x] COLOR_MINE = (200, 50, 200) magenta

### Rendering System
- [x] ProjectileRenderer class for missiles and mines
- [x] render_all_missiles() with viewport culling
- [x] render_all_mines() with viewport culling
- [x] render_visible_missiles() with fog filtering
- [x] render_visible_mines() with fog filtering
- [x] Integration with RenderPipeline
- [x] Integration with all camera modes
- [x] Zoom scaling for missiles and mines
- [x] HUD weapon status display

### Physics & Collision
- [x] Swept collision for missiles (fast movement)
- [x] Wall collision detection (immediate destruction)
- [x] Tank collision detection (apply damage)
- [x] Mine proximity detection (enemy tanks)
- [x] Mine impact trigger (from bullets/missiles)
- [x] Blast radius damage calculations
- [x] Mine arm delay to prevent self-trigger
- [x] Viewport culling optimization

### Code Quality
- [x] Full type annotations throughout
- [x] Google-style docstrings
- [x] Passes Ruff linting
- [x] Organized into appropriate modules
- [x] Consistent with existing code style
- [x] Backward compatible with Phase 4

## Phase 5 Implementation Details

### Missile Architecture
- Inherits from Entity like Bullet
- Stores owner_id for tracking shooter
- Uses swept collision detection (prev_x, prev_y)
- Immediate destruction on wall collision (no bounce)
- Higher speed allows strategic long-range attacks
- 1-shot maximum per cooldown (tactical limitation)

### Mine Architecture
- Inherits from Entity
- Stores owner_id for non-friendly triggering
- 1-second armed delay prevents immediate self-trigger
- Stationary on map (no velocity)
- Blast radius affects all non-friendly tanks at detonation
- Can be triggered by player fire (mines for static defense)
- Ammo-limited (3 max) for balancing
- Works in fog (visible through radar)

### Collision System
- check_missile_wall_collision() - swept detection
- check_missile_tank_collision() - circle-circle test
- check_mine_proximity() - distance-based trigger
- check_mine_collision_with_projectile() - projectile impact
- All checks respect ownership (no friendly fire)

### Perception Integration
- Mines appear in visible_entities if in vision
- Missiles appear in visible_entities if in vision
- Both detectable by radar (600px range, team-filtered)
- Included in sensor snapshots for bots
- Kind strings: "missile", "mine" for identification

## Testing Notes
- Game starts without errors
- Syntax validation passed
- All imports resolve correctly
- Backward compatible with existing code
- Demo modes work with new weapons
- HUD displays weapon status correctly

## Known Issues
None currently identified.

## Future Enhancements
- [ ] **Weapon Upgrades**: Temporary power-ups for increased weapon power
- [ ] **Homing Missiles**: Guided missiles that track enemies
- [ ] **Shield Boost**: Temporary damage reduction
- [ ] **Ammo Drops**: Random pickups on map for mine/missile refills
- [ ] **Laser**: Instant-hit hitscan weapon with line effect
- [ ] **Grenade Launcher**: Arc projectile with impact detonation

## Phase 5 Review
All objectives met. Weapon system is balanced and integrated with:
- Two new weapon types (missiles and mines)
- Complete physics and collision handling
- Full sensor system integration
- Proper UI feedback and control bindings
- Stats tracking for new weapons
- Backward compatibility with existing code
- Clean architecture supporting future weapon additions

---


### Planned Features (Future Phases)
- [ ] **Bot API extension**: Add mine_placement and shoot_missile actions to BotAction
- [ ] **Sensor updates**: Mines visible to radar in BotState.radar_hits

### Implementation Notes
- Mines should be a new entity type (inherit from Entity)
- Missiles can extend Bullet with higher speed, no bounce, higher damage
- Need new collision handling for mine proximity triggers
- Bot API needs new action flags: `place_mine: bool`, `shoot_missile: bool`
- UI should show mine count and missile cooldown alongside bullet cooldown

---

## Future: Phase 6 - Reinforcement Learning & Self-Play

### Planned Features
- [ ] **Self-play training**: Bots learn by competing against copies of themselves
- [ ] **Competitive co-evolution**: Multiple agents training simultaneously (dueling architecture)
- [ ] **Reward system**: Damage dealt, survival time, kills, match victory
- [ ] **Training infrastructure**: Episode management, checkpoint saving, resume training
- [ ] **Neural network integration**: PyTorch or TensorFlow policy networks
- [ ] **Experience replay buffer**: Store and sample battle episodes for training
- [ ] **Dueling DQN**: Separate value and advantage network streams
- [ ] **Policy gradient methods**: PPO, A3C, or similar for continuous action spaces
- [ ] **Training visualization**: Reward curves, win rates, learning progress dashboards
- [ ] **Automated training arena**: Headless matches between learning agents
- [ ] **ELO rating system**: Track bot skill levels during training

### Implementation Notes
- Self-play: Bot plays against previous versions of itself
- Competitive training: 2+ bots evolve together (arms race dynamics)
- Need Phase 4 external bot runner for training isolation
- Performance metrics essential for reward signal design
- Consider starting with simple reward: survive + damage_dealt - damage_taken
- Bots should learn to use mines and missiles effectively (needs Phase 5)

---

## Future: Phase 7+ - Advanced Features & Tournaments

### Planned Features
- Power-ups (speed, shield, health)
- Genetic algorithms for bot evolution
- Full tournament system with brackets
- Bot marketplace/sharing
