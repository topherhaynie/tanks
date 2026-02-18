# Game Architecture Plan

## Core Modules

/engine - game_loop.py - physics.py - rendering.py - fog_of_war.py -
sensors.py - map_loader.py

/bots - python_bot/ - cpp_bot/

/maps - arena maps - maze maps

/modes - duel - arena - level

## Rendering Layers

1.  Map
2.  Fog of war
3.  Obstacles
4.  Tanks
5.  Bullets
6.  Vision & radar overlays
7.  Debug info

## Timing

-   Fixed timestep (\~30 ticks/sec)
-   Bots must respond within time limit
-   Deterministic physics
