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
-   Map loader and generator

## Phase 5 --- Advanced Features

-   Mines
-   Heavy weapon
-   Radar upgrades
-   Better sensors

## Phase 6 --- AI Expansion

-   Bot tournaments
-   Ranking system
-   Reinforcement learning
-   Genetic evolution
