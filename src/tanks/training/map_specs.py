"""Map specifications for training phases.

Defines preset map configurations for different training scenarios.
Each spec focuses on developing specific combat skills.
"""

from dataclasses import dataclass

from tanks.maps.generator import GeneratorConfig, MapSize, TerrainPattern


@dataclass
class TrainingMapSpec:
    """Specification for a training map."""

    name: str
    description: str
    config: GeneratorConfig
    skill_focus: list[str]  # What skills this map teaches
    recommended_opponent: str = "smart"  # "smart" or "simple" or "self-play"
    success_threshold: float = 0.70  # Win rate to advance
    min_episodes: int = 100  # Minimum episodes before advancing


# =============================================================================
# PHASE A: Map-Specific Skill Training
# =============================================================================

CLOSE_COMBAT_SPEC = TrainingMapSpec(
    name="Close Combat Arena",
    description="Dense obstacles force close-range engagements",
    config=GeneratorConfig(
        width=25,
        height=15,
        pattern=TerrainPattern.SCATTERED,
        obstacle_density=0.35,
        border_walls=True,
        symmetry=True,
        num_spawn_points=4,  # Support up to 4 tanks
    ),
    skill_focus=[
        "Close-range combat",
        "Corner fighting",
        "Ricochet shots",
        "Obstacle usage for cover",
    ],
    recommended_opponent="smart",
    success_threshold=0.70,
    min_episodes=100,
)

OPEN_ARENA_SPEC = TrainingMapSpec(
    name="Open Arena",
    description="Minimal obstacles emphasize positioning and long-range combat",
    config=GeneratorConfig(
        width=50,
        height=30,
        pattern=TerrainPattern.OPEN_ARENA,
        obstacle_density=0.08,
        border_walls=True,
        symmetry=True,
        num_spawn_points=4,
    ),
    skill_focus=[
        "Long-range combat",
        "Positioning",
        "Evasive maneuvers",
        "Target leading",
    ],
    recommended_opponent="smart",
    success_threshold=0.70,
    min_episodes=100,
)

MAZE_SPEC = TrainingMapSpec(
    name="Maze Arena",
    description="Complex corridors require navigation and ambush tactics",
    config=GeneratorConfig(
        width=35,
        height=25,
        pattern=TerrainPattern.MAZE,
        obstacle_density=0.30,
        border_walls=True,
        symmetry=False,  # Asymmetric for exploration challenge
        num_spawn_points=4,
    ),
    skill_focus=[
        "Navigation",
        "Radar usage",
        "Ambush tactics",
        "Exploration",
    ],
    recommended_opponent="self-play",
    success_threshold=0.65,
    min_episodes=150,
)

FORTRESS_SPEC = TrainingMapSpec(
    name="Fortress Arena",
    description="Central structure with defensive positions",
    config=GeneratorConfig(
        width=40,
        height=28,
        pattern=TerrainPattern.FORTRESS,
        obstacle_density=0.20,
        border_walls=True,
        symmetry=True,
        num_spawn_points=4,
    ),
    skill_focus=[
        "Territory control",
        "Defensive positioning",
        "Strategic advancement",
    ],
    recommended_opponent="self-play",
    success_threshold=0.60,
    min_episodes=150,
)

ROOMS_SPEC = TrainingMapSpec(
    name="Room Complex",
    description="Connected rooms with chokepoints",
    config=GeneratorConfig(
        width=45,
        height=30,
        pattern=TerrainPattern.ROOMS,
        obstacle_density=0.25,
        border_walls=True,
        symmetry=True,
        num_spawn_points=4,
    ),
    skill_focus=[
        "Room clearing",
        "Chokepoint control",
        "Multi-room tactics",
    ],
    recommended_opponent="self-play",
    success_threshold=0.65,
    min_episodes=150,
)

MIXED_SPEC = TrainingMapSpec(
    name="Mixed Tactics Arena",
    description="Combination of all terrain types for general combat",
    config=GeneratorConfig(
        width=40,
        height=25,
        pattern=TerrainPattern.SCATTERED,
        obstacle_density=0.25,
        border_walls=True,
        symmetry=True,
        num_spawn_points=4,
    ),
    skill_focus=[
        "Adaptability",
        "General combat",
        "All-around skills",
    ],
    recommended_opponent="self-play",
    success_threshold=0.75,
    min_episodes=150,
)

# =============================================================================
# PHASE C: Survival Training Specs (1v2, 1v3)
# =============================================================================

SURVIVAL_SMALL_SPEC = TrainingMapSpec(
    name="Close Quarters Survival",
    description="1v2 survival in close quarters",
    config=GeneratorConfig(
        width=35,
        height=20,
        pattern=TerrainPattern.SCATTERED,
        obstacle_density=0.30,
        border_walls=True,
        symmetry=False,
        num_spawn_points=3,  # 1 agent + 2 opponents
    ),
    skill_focus=[
        "Survival tactics",
        "1vN combat",
        "Defensive positioning",
    ],
    recommended_opponent="self-play",
    success_threshold=0.30,  # Lower threshold for outnumbered scenario
    min_episodes=200,
)

SURVIVAL_MEDIUM_SPEC = TrainingMapSpec(
    name="Tactical Survival",
    description="1v2 survival with corridors",
    config=GeneratorConfig(
        width=50,
        height=28,
        pattern=TerrainPattern.CORRIDORS,
        obstacle_density=0.25,
        border_walls=True,
        symmetry=False,
        num_spawn_points=3,
    ),
    skill_focus=[
        "Tactical retreat",
        "Area denial",
        "Focus fire evasion",
    ],
    recommended_opponent="self-play",
    success_threshold=0.25,
    min_episodes=200,
)

SURVIVAL_EXTREME_SPEC = TrainingMapSpec(
    name="Extreme Survival",
    description="1v3 survival in maze",
    config=GeneratorConfig(
        width=60,
        height=34,
        pattern=TerrainPattern.MAZE,
        obstacle_density=0.30,
        border_walls=True,
        symmetry=False,
        num_spawn_points=4,  # 1 agent + 3 opponents
    ),
    skill_focus=[
        "Extreme survival",
        "1v3 tactics",
        "Ambush defense",
    ],
    recommended_opponent="self-play",
    success_threshold=0.20,
    min_episodes=200,
)

# =============================================================================
# PHASE B: Random Map Configurations
# =============================================================================


# For backwards compatibility
def create_random_map_config(**kwargs) -> GeneratorConfig:
    """Create random map config supporting both old and new call styles.

    Supports:
    - New style: size=MapSize.MEDIUM, min_density=..., max_density=..., num_opponents=...
    - Legacy style: min_size=(w, h), max_size=(w, h), min_density=..., max_density=...
    """
    import random

    if "min_size" in kwargs or "max_size" in kwargs:
        min_width, min_height = kwargs.get("min_size", (30, 17))
        max_width, max_height = kwargs.get("max_size", (60, 34))
        min_density = kwargs.get("min_density", 0.10)
        max_density = kwargs.get("max_density", 0.35)
        allow_patterns = kwargs.get("allow_patterns")
        num_opponents = kwargs.get("num_opponents", 1)

        if allow_patterns is None:
            allow_patterns = list(TerrainPattern)

        width = random.randint(int(min_width), int(max_width))
        height = random.randint(int(min_height), int(max_height))
        density = random.uniform(min_density, max_density)
        pattern = random.choice(allow_patterns)
        symmetry = random.choice([True, False])

        return GeneratorConfig(
            width=max(20, width),
            height=max(15, height),
            pattern=pattern,
            obstacle_density=density,
            border_walls=True,
            symmetry=symmetry,
            num_spawn_points=num_opponents + 1,
        )

    return get_random_map_config(**kwargs)


def get_random_map_config(
    size: MapSize = MapSize.MEDIUM,
    allow_patterns: list[TerrainPattern] | None = None,
    min_density: float = 0.10,
    max_density: float = 0.35,
    num_opponents: int = 1,
) -> GeneratorConfig:
    """Generate random map configuration for generalization training.

    Args:
        size: Base map size (can add variance).
        allow_patterns: Allowed patterns (all if None).
        min_density: Minimum obstacle density.
        max_density: Maximum obstacle density.
        num_opponents: Number of opponents (determines spawn points).

    Returns:
        Random GeneratorConfig for varied training.

    """
    import random

    # Random pattern
    if allow_patterns is None:
        allow_patterns = list(TerrainPattern)

    pattern = random.choice(allow_patterns)

    # Random size variance (±20%)
    base_width, base_height = size.value
    width_variance = int(base_width * 0.2)
    height_variance = int(base_height * 0.2)

    width = base_width + random.randint(-width_variance, width_variance)
    height = base_height + random.randint(-height_variance, height_variance)

    # Ensure minimum size
    width = max(20, width)
    height = max(15, height)

    # Random density
    density = random.uniform(min_density, max_density)

    # Random symmetry
    symmetry = random.choice([True, False])

    return GeneratorConfig(
        width=width,
        height=height,
        pattern=pattern,
        obstacle_density=density,
        border_walls=True,
        symmetry=symmetry,
        num_spawn_points=num_opponents + 1,  # Agent + opponents
    )


# =============================================================================
# Common Training Specs
# =============================================================================

ALL_STATIC_SPECS = [
    CLOSE_COMBAT_SPEC,
    OPEN_ARENA_SPEC,
    MAZE_SPEC,
    FORTRESS_SPEC,
    ROOMS_SPEC,
    MIXED_SPEC,
]

# Phase A: Standard 6-stage curriculum
STANDARD_CURRICULUM = [
    CLOSE_COMBAT_SPEC,
    OPEN_ARENA_SPEC,
    MAZE_SPEC,
    ROOMS_SPEC,
    FORTRESS_SPEC,
    MIXED_SPEC,
]


def get_spec_by_name(name: str) -> TrainingMapSpec | None:
    """Get map spec by name.

    Args:
        name: Map spec name.

    Returns:
        TrainingMapSpec if found, None otherwise.

    """
    for spec in ALL_STATIC_SPECS:
        if spec.name == name:
            return spec
    return None
