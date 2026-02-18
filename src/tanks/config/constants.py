"""Game constants - tunable parameters for gameplay."""

# Display Settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Tank Battle"
FPS = 60
TICKS_PER_SECOND = 30  # Fixed physics timestep (for backward compatibility)
PHYSICS_RATE = 120  # Physics updates per second (high for accuracy)
INPUT_RATE = 30  # Input sampling rate (for determinism)

# Tile System
TILE_SIZE = 64  # pixels
FOG_TILE_SIZE = 32  # pixels for fog of war (smaller = more detail)
TILE_EMPTY = 0
TILE_WALL_HORIZONTAL = 1
TILE_WALL_VERTICAL = 2
TILE_WALL_DIAGONAL_NE = 3  # NE-SW diagonal
TILE_WALL_DIAGONAL_NW = 4  # NW-SE diagonal
TILE_WALL_SOLID = 5  # Solid square wall

# Tank Parameters
TANK_RADIUS = 20  # pixels (circle hitbox)
TANK_MAX_SPEED = 150  # pixels per second
TANK_TURN_RATE = 180  # degrees per second
TURRET_TURN_RATE = 270  # degrees per second
TANK_MAX_HP = 3

# Shooting Parameters
BULLET_SPEED = 400  # pixels per second
BULLET_RADIUS = 4  # pixels
BULLET_DAMAGE = 1
BULLET_LIFETIME = 3.0  # seconds
SHOOT_COOLDOWN = 0.5  # seconds between shots
MAX_BULLET_BOUNCES = 1

# Vision System
VISION_RADIUS = 200  # pixels
RADAR_RADIUS = 600  # pixels

# Color definitions (RGB tuples)
COLOR_BACKGROUND = (40, 40, 50)
COLOR_WALL = (100, 100, 120)
COLOR_TANK_FRIENDLY = (50, 150, 50)
COLOR_TANK_ENEMY = (200, 50, 50)
COLOR_BULLET = (255, 255, 100)
COLOR_FOG = (0, 0, 0, 240)  # With alpha - very dark
COLOR_VISION_OVERLAY = (100, 255, 100, 30)
COLOR_RADAR_OVERLAY = (100, 100, 255, 20)
COLOR_RADAR_BLIP = (100, 200, 255, 200)
COLOR_RADAR_SWEEP = (100, 200, 255, 60)

# Debug Colors
COLOR_DEBUG_HITBOX = (255, 0, 255)
COLOR_DEBUG_LINE = (0, 255, 255)
