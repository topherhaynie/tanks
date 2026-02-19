"""Render pipeline orchestration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RenderContext:
    """Bundle render inputs for a single frame."""

    game_state: Any
    camera: Any
    perspective_tank: Any
    observer_tanks: Any
    observer_fog_opacity: float
    observer_fog_colors: Any
    observer_hidden_alpha: float
    settings: Any
    current_time: float
    stats_tracker: Any = None  # Optional stats tracker for live stats display


class RenderPipeline:
    """Orchestrate render layers and visibility rules."""

    def __init__(
        self,
        map_renderer: Any,
        bullet_renderer: Any,
        tank_renderer: Any,
        effects_renderer: Any,
        fog_renderer: Any,
        radar_renderer: Any,
        minimap_renderer: Any,
        debug_renderer: Any,
        hud_renderer: Any,
        projectile_renderer: Any,
    ) -> None:
        """Initialize pipeline with renderer dependencies.

        Args:
            map_renderer: Renderer for map tiles.
            bullet_renderer: Renderer for bullets.
            tank_renderer: Renderer for tanks.
            effects_renderer: Renderer for effects.
            fog_renderer: Renderer for fog of war.
            radar_renderer: Renderer for radar overlays.
            minimap_renderer: Renderer for minimap overlays.
            debug_renderer: Renderer for debug overlays.
            hud_renderer: Renderer for HUD elements.
            projectile_renderer: Renderer for missiles and mines.

        """
        self._map_renderer = map_renderer
        self._bullet_renderer = bullet_renderer
        self._tank_renderer = tank_renderer
        self._effects_renderer = effects_renderer
        self._fog_renderer = fog_renderer
        self._radar_renderer = radar_renderer
        self._minimap_renderer = minimap_renderer
        self._debug_renderer = debug_renderer
        self._hud_renderer = hud_renderer
        self._projectile_renderer = projectile_renderer

    def render(self, context: RenderContext) -> None:
        """Render a full frame's worth of layers.

        Args:
            context: Render inputs for this frame.

        """
        # Layer 1: Map
        self._map_renderer.render(context.game_state.game_map, context.camera)

        # Layer 2: Entities
        self._render_entities(context)

        # Layer 2.5: Visual effects
        self._effects_renderer.render(context.game_state.effects)

        # Layer 2.7: Fog of war
        self._render_fog(context)

        # Layer 2.8-2.9: Radar and minimap
        if context.perspective_tank and context.settings.show_radar_blips:
            self._radar_renderer.render_blips(
                context.perspective_tank,
                context.current_time,
            )

        if context.settings.show_radar_blips:
            self._radar_renderer.render_jamming_effects(context.game_state.tanks)

        if context.perspective_tank and context.settings.show_minimap:
            self._minimap_renderer.render(
                context.game_state,
                context.perspective_tank,
                context.current_time,
            )

        # Layer 3: Debug and HUD
        self._render_debug_and_hud(context)

    def _render_entities(self, context: RenderContext) -> None:
        """Render bullets, missiles, mines and tanks with appropriate visibility filtering.

        Args:
            context: Render inputs for this frame.

        """
        if context.observer_tanks:
            self._bullet_renderer.render_all(context.game_state.bullets, context.camera)
            self._projectile_renderer.render_all_missiles(
                context.game_state.missiles,
                context.camera,
            )
            self._projectile_renderer.render_all_mines(
                context.game_state.mines,
                context.camera,
            )
            self._tank_renderer.render_observer(
                context.game_state.tanks,
                context.observer_tanks,
                context.observer_hidden_alpha,
                context.camera,
            )
        elif context.perspective_tank:
            self._bullet_renderer.render_visible(
                context.game_state.bullets,
                context.perspective_tank,
                context.camera,
            )
            self._projectile_renderer.render_visible_missiles(
                context.game_state.missiles,
                context.perspective_tank,
                context.camera,
            )
            self._projectile_renderer.render_visible_mines(
                context.game_state.mines,
                context.perspective_tank,
                context.camera,
            )
            self._tank_renderer.render_visible(
                context.game_state.tanks,
                context.perspective_tank,
                context.camera,
            )
        else:
            self._bullet_renderer.render_all(context.game_state.bullets, context.camera)
            self._projectile_renderer.render_all_missiles(
                context.game_state.missiles,
                context.camera,
            )
            self._projectile_renderer.render_all_mines(
                context.game_state.mines,
                context.camera,
            )
            self._tank_renderer.render_all(context.game_state.tanks, context.camera)

    def _render_fog(self, context: RenderContext) -> None:
        """Render fog of war for observer or perspective view.

        Args:
            context: Render inputs for this frame.

        """
        if context.observer_tanks:
            fog_colors = context.observer_fog_colors or (
                (80, 120, 255),
                (255, 120, 120),
            )
            # Use new observer fog rendering with proper color mixing
            self._fog_renderer.render_observer_fog(
                context.game_state.game_map,
                context.observer_tanks,
                fog_colors,
                undiscovered_opacity=0.4,  # More transparent fog for undiscovered areas
                team_tint_opacity=0.15,  # Light colored tint for team-discovered areas
            )
        elif context.perspective_tank and context.perspective_tank.fog_memory:
            self._fog_renderer.render(
                context.game_state.game_map,
                context.perspective_tank,
            )

    def _render_debug_and_hud(self, context: RenderContext) -> None:
        """Render debug overlays and HUD elements.

        Args:
            context: Render inputs for this frame.

        """
        if context.settings.show_hitboxes:
            self._debug_renderer.render_hitboxes(context.game_state)

        if context.settings.show_vision and context.perspective_tank:
            self._radar_renderer.render_vision_debug(context.perspective_tank)

        if context.settings.show_fps:
            self._hud_renderer.render_fps(context.game_state.fps)

        if context.perspective_tank:
            self._hud_renderer.render_jamming_status(context.perspective_tank)
            self._hud_renderer.render_weapon_status(context.perspective_tank)

        if context.settings.show_stats and context.stats_tracker:
            self._hud_renderer.render_stats_overlay(
                context.stats_tracker,
                context.game_state.tanks,
            )
