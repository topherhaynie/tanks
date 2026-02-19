# Development Roadmap

## Phase 1 --- Core Engine (Complete)

-   Basic pygame window
-   Tank movement
-   Collision and sliding
-   Shooting and ricochet
-   Bullet damage

## Phase 2 --- Perception (Complete)

-   Vision system
-   Fog of war
-   Terrain memory
-   Radar detection

## Phase 3 --- Bot Framework (Complete)

-   Bot controller base class (integrates with input system)
-   Sensor API for bot inputs (vision, radar, fog memory)
-   Python bot API with dataclasses and Protocol
-   Simple bot implementation (wander/seek with randomness)
-   Smart bot implementation (radar pursuit, stuck detection)
-   Observer visibility modes (global and perspective)
-   Observer rendering with dual fog overlays
-   Demo modes (2-player, player-vs-bot, bot-vs-bot)
-   External bot protocol documentation (JSON schema)

## Phase 4 --- External Bots and Game Modes

-   **External Bot Runner**: subprocess management for C++/other languages
-   **JSON IPC**: stdin/stdout communication (protocol already documented)
-   **Bot timeout handling**: watchdog for slow/hanging bots
-   **C++ bot SDK**: headers, example bot, CMake build
-   Bot performance metrics (kills, deaths, accuracy, damage)
-   Tournament mode framework (scheduling, ranking, leaderboards)
-   Line-of-sight precision (center-to-edge visibility)
-   Arena mode (multi-tank battles)
-   Level mode with objectives
-   **Camera System**: Support for larger maps
    -   Follow camera: tracks single tank smoothly (for player perspective)
    -   Pan and zoom controls for player camera
    -   Screen-space bounds with smooth scrolling
    -   Global camera: captures entire map (for observer/training view)
    -   Minimap always shows full map regardless of camera
    -   Camera configuration per game mode (follow vs. global)
-   **Advanced Map System**: 
    -   Procedural map generator with configurable parameters
    -   Multiple map sizes (small: 20x11, medium: 40x22, large: 80x44+)
    -   Varied terrain patterns (open arena, maze, corridors, rooms)
    -   Obstacle density and distribution controls
    -   Spawn point balancing (fair starting positions)
    -   JSON map format loader (save/load custom maps)
    -   Map validation (reachability, balance checks)
    -   Map prefabs library (tournament-ready maps)

## Phase 5 --- Weapons & Items

-   **Mines**: Deployable explosives
    -   Placeable by tanks (mine button/action)
    -   Detectable by radar (show up as radar blips)
    -   Damage radius on detonation
    -   Limited mine capacity per tank (e.g., 3 mines max)
    -   Longer cooldown than shooting (e.g., 5 seconds)
    -   Persist on map until triggered or destroyed
    -   Trigger on proximity or bullet impact
-   **Missiles**: High-damage projectiles
    -   Fast speed (2-3x bullet speed)
    -   Longer cooldown than standard bullets (e.g., 3-5 seconds)
    -   No ricochet (explode on first impact)
    -   Higher damage than bullets (e.g., 50 vs 25)
    -   Visual distinction (larger, different color)
    -   Separate missile action/button
-   **Weapon selection system**: Switch between bullet/missile modes
-   **Ammo/cooldown UI**: Display available weapons and cooldowns
-   **Bot API extension**: Expose mine placement and missile actions to bots
-   **Sensor updates**: Bots can detect mines via radar

## Phase 6 --- Reinforcement Learning & Self-Play

-   **Self-play training framework**: bots learn by playing against themselves
-   **Competitive co-evolution**: multiple agents training simultaneously
-   **Reward system**: damage dealt, survival time, kills, victory
-   **Training infrastructure**: episode management, checkpoint saving
-   **Neural network integration**: PyTorch/TensorFlow policy networks
-   **Experience replay**: store and sample battle episodes
-   **Dueling DQN architecture**: separate value and advantage streams
-   **Policy gradient methods**: PPO or similar for continuous actions
-   **Training visualization**: reward curves, win rates, learning progress
-   **Bot arena for training**: automated matches between learning agents
-   **Evaluation metrics**: ELO rating, tournament performance tracking

## Phase 7 --- Advanced Features & Upgrades

-   Power-ups (speed boost, shield, etc.)
-   Radar upgrades (longer range, faster refresh)
-   Better sensors (thermal vision, motion detection)
-   Tank customization (armor, speed, firepower tradeoffs)

## Phase 8 --- AI Expansion & Tournaments

-   Bot tournaments (bracket-style, round-robin)
-   Ranking system and leaderboards
-   Genetic algorithms for bot evolution
-   Population-based training variants
-   Bot marketplace/sharing system
