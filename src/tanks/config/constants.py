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
FOG_TILE_SIZE = 16  # pixels for fog of war (smaller = more detail)
FOG_GRADIENT_SCALE = (
    1.7  # Multiplier for fog gradient stamp size (1.0 = same as FOG_TILE_SIZE)
)
TILE_EMPTY = 0
TILE_WALL_HORIZONTAL = 1
TILE_WALL_VERTICAL = 2
TILE_WALL_DIAGONAL_NE = 3  # NE-SW diagonal
TILE_WALL_DIAGONAL_NW = 4  # NW-SE diagonal
TILE_WALL_SOLID = 5  # Solid square wall

# Tank Parameters
TANK_RADIUS = 20  # pixels (circle hitbox)
TANK_MAX_SPEED = 100  # pixels per second
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
VISION_RADIUS = 150  # pixels - fog revelation range (active vision)
ENTITY_VISION_RADIUS = 600  # pixels - extended entity vision through revealed areas
RADAR_RADIUS = 400  # pixels - actual radar detection range
RADAR_VISUAL_RADIUS = (
    50  # pixels - visual radar circle radius (can differ from detection for tactics)
)
RADAR_JAMMING_RADIUS = 350  # pixels - radius within which jamming affects enemy radar
RADAR_JAMMING_DURATION = 3.0  # seconds - how long jamming lasts
RADAR_JAMMING_COOLDOWN = 10.0  # seconds - cooldown between jamming uses
RADAR_SWEEP_SPEED = 270  # degrees per second (clockwise in screen coordinates)
RADAR_BLIP_FADE_TIME = 2.0  # seconds - how long blips take to fade
RADAR_SWEEP_WIDTH = 20  # degrees - width of the sweep arc

# Minimap Settings
MINIMAP_SIZE = 200  # Minimap width/height in pixels
MINIMAP_PADDING = 20  # Distance from screen edges
MINIMAP_POSITION = "bottom-right"  # Position on screen
MINIMAP_MIN_REVEALED_FOG_TILES = 3  # Minimum fog tiles revealed to show wall (out of 4)

# Color definitions (RGB tuples)
COLOR_BACKGROUND = (40, 40, 50)
COLOR_WALL = (100, 100, 120)
COLOR_TANK_FRIENDLY = (50, 150, 50)
COLOR_TANK_ENEMY = (200, 50, 50)
COLOR_BULLET = (255, 255, 100)
COLOR_FOG = (0, 0, 0, 255)  # With alpha - very dark
COLOR_VISION_OVERLAY = (100, 255, 100, 30)
COLOR_RADAR_OVERLAY = (100, 100, 255, 20)
COLOR_RADAR_BLIP = (100, 200, 255, 200)
COLOR_RADAR_BLIP_TANK = (100, 200, 255, 200)  # Cyan for tanks
COLOR_RADAR_BLIP_MINE = (255, 150, 50, 200)  # Orange for mines
COLOR_RADAR_SWEEP = (100, 200, 255, 60)
COLOR_RADAR_SWEEP_BAR = (80, 180, 80, 100)  # Toned down green sweep line
COLOR_RADAR_JAMMING = (255, 100, 100, 150)  # Red for jamming effect

# Minimap Colors
COLOR_MINIMAP_BACKGROUND = (20, 20, 30, 180)
COLOR_MINIMAP_BORDER = (100, 100, 120, 255)
COLOR_MINIMAP_WALL = (80, 80, 100, 255)
COLOR_MINIMAP_TANK_FRIENDLY = (50, 200, 50, 255)
COLOR_MINIMAP_TANK_ENEMY = (200, 50, 50, 255)
COLOR_MINIMAP_RADAR_RANGE = (100, 100, 255, 60)
COLOR_MINIMAP_VISION_RANGE = (100, 255, 100, 60)

# Debug Colors
COLOR_DEBUG_HITBOX = (255, 0, 255)
COLOR_DEBUG_LINE = (0, 255, 255)
