"""Render pipeline orchestration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RenderContext:
    """Bundle render inputs for a single frame."""

    game_state: Any
    perspective_tank: Any
    settings: Any
    current_time: float


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

    def render(self, context: RenderContext) -> None:
        """Render a full frame's worth of layers.

        Args:
            context: Render inputs for this frame.

        """
        # Layer 1: Map
        self._map_renderer.render(context.game_state.game_map)

        # Layer 2: Entities (filtered by visibility if in fog mode)
        if context.perspective_tank:
            self._bullet_renderer.render_visible(context.game_state.bullets, context.perspective_tank)
            self._tank_renderer.render_visible(context.game_state.tanks, context.perspective_tank)
        else:
            self._bullet_renderer.render_all(context.game_state.bullets)
            self._tank_renderer.render_all(context.game_state.tanks)

        # Layer 2.5: Visual effects
        self._effects_renderer.render(context.game_state.effects)

        # Layer 2.7: Fog of war
        if context.perspective_tank and context.perspective_tank.fog_memory:
            self._fog_renderer.render(context.game_state.game_map, context.perspective_tank)

        # Layer 2.8: Radar blips (on top of fog since radar sees through walls)
        if context.perspective_tank and context.settings.show_radar_blips:
            self._radar_renderer.render_blips(context.perspective_tank, context.current_time)

        # Layer 2.85: Radar jamming effects
        if context.settings.show_radar_blips:
            self._radar_renderer.render_jamming_effects(context.game_state.tanks)

        # Layer 2.9: Minimap with radar overlay
        if context.perspective_tank and context.settings.show_minimap:
            self._minimap_renderer.render(context.game_state, context.perspective_tank, context.current_time)

        # Layer 3: Debug overlays
        if context.settings.show_hitboxes:
            self._debug_renderer.render_hitboxes(context.game_state)

        if context.settings.show_vision and context.perspective_tank:
            self._radar_renderer.render_vision_debug(context.perspective_tank)

        if context.settings.show_fps:
            self._hud_renderer.render_fps(context.game_state.fps)

        # Render jamming status for perspective tank
        if context.perspective_tank:
            self._hud_renderer.render_jamming_status(context.perspective_tank)
