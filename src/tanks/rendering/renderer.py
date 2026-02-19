"""Main renderer coordinating all drawing."""

import time
from typing import TYPE_CHECKING, Any

import pygame

from tanks.rendering.bullets import BulletRenderer
from tanks.rendering.debug import DebugRenderer
from tanks.rendering.effects_renderer import EffectsRenderer
from tanks.rendering.fog import FogRenderer
from tanks.rendering.frame import FrameRenderer
from tanks.rendering.hud import HudRenderer
from tanks.rendering.map_renderer import MapRenderer
from tanks.rendering.minimap import MinimapRenderer
from tanks.rendering.pipeline import RenderContext, RenderPipeline
from tanks.rendering.radar import RadarRenderer
from tanks.rendering.tanks import TankRenderer

if TYPE_CHECKING:
    from tanks.entities.tank import Tank


class Renderer:
    """Handles all game rendering."""

    def __init__(self, screen: pygame.Surface, settings: Any) -> None:
        """Initialize renderer.

        Args:
            screen: Pygame surface to render to.
            settings: Game settings object.

        """
        self.screen = screen
        self.settings = settings
        self.font = None
        self.perspective_tank = None  # Tank from whose perspective to render fog
        self.observer_tanks = None
        self.observer_fog_opacity = 1.0
        self.observer_fog_colors = None
        self.observer_hidden_alpha = 1.0

        # Initialize font for debug text
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        self.minimap_renderer = MinimapRenderer(self.screen)
        self.radar_renderer = RadarRenderer(self.screen, self.small_font)
        self.hud_renderer = HudRenderer(self.screen, self.small_font)
        self.tank_renderer = TankRenderer(self.screen)
        self.bullet_renderer = BulletRenderer(self.screen)
        self.map_renderer = MapRenderer(self.screen)
        self.debug_renderer = DebugRenderer(self.screen)
        self.effects_renderer = EffectsRenderer(self.screen)
        self.fog_renderer = FogRenderer(self.screen)
        self.frame_renderer = FrameRenderer(self.screen)
        self.pipeline = RenderPipeline(
            self.map_renderer,
            self.bullet_renderer,
            self.tank_renderer,
            self.effects_renderer,
            self.fog_renderer,
            self.radar_renderer,
            self.minimap_renderer,
            self.debug_renderer,
            self.hud_renderer,
        )

    def render_frame(self, game_state: Any) -> None:
        """Render a complete frame.

        Args:
            game_state: Current game state to render.

        """
        self.frame_renderer.begin()

        context = RenderContext(
            game_state=game_state,
            perspective_tank=self.perspective_tank,
            observer_tanks=self.observer_tanks,
            observer_fog_opacity=self.observer_fog_opacity,
            observer_fog_colors=self.observer_fog_colors,
            observer_hidden_alpha=self.observer_hidden_alpha,
            settings=self.settings,
            current_time=time.time(),
        )
        self.pipeline.render(context)

        self.frame_renderer.end()

    def set_perspective_tank(self, tank: "Tank | None") -> None:
        """Set which tank's perspective to render fog from.

        Args:
            tank: Tank to render perspective from, or None for no fog.

        """
        self.perspective_tank = tank

    def set_observer_view(
        self,
        tanks: list["Tank"] | None,
        fog_opacity: float = 1.0,
        fog_colors: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None,
        hidden_alpha: float = 1.0,
    ) -> None:
        """Set observer view parameters for multi-perspective rendering.

        Args:
            tanks: Tanks to use for observer fog layers, or None to disable.
            fog_opacity: Opacity scale for fog overlays.
            fog_colors: RGB colors to tint each fog layer.
            hidden_alpha: Alpha for tanks hidden from opponents.

        """
        self.observer_tanks = tanks
        self.observer_fog_opacity = fog_opacity
        self.observer_fog_colors = fog_colors
        self.observer_hidden_alpha = hidden_alpha
