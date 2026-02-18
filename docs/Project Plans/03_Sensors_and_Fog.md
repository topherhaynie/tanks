# Sensor & Fog of War System (v2)

## Vision System

-   Circular radius (medium)
-   Blocked by walls (line of sight)
-   Reveals terrain permanently
-   Enemies, bullets, and mines visible only while in sight

### Bot Receives

-   Self state (position, angles, HP, cooldown)
-   Visible enemies (distance, relative angles)
-   Wall distances (forward, left, right)
-   Incoming bullet warning (if visible)

## Fog Memory

-   Terrain discovery stored per tank
-   Enemies and bullets NOT remembered

## Radar System

-   Larger radius than vision
-   Not blocked by walls
-   Detects tanks and mines only
-   Does NOT reveal terrain
-   Does NOT persist memory
-   Provides approximate distance and angle

## Gameplay Effects

-   Exploration
-   Tracking enemies
-   Ambush tactics
-   Mine detection
