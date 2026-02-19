"""HUD rendering helpers."""

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from tanks.core.stats import StatsTracker
    from tanks.entities.tank import Tank


class HudRenderer:
    """Draw HUD elements like FPS and status text."""

    def __init__(self, screen: pygame.Surface, small_font: pygame.font.Font) -> None:
        """Initialize HUD renderer.

        Args:
            screen: Pygame surface to render to.
            small_font: Font for HUD text.

        """
        self._screen = screen
        self._small_font = small_font

    def render_fps(self, fps: float) -> None:
        """Render FPS counter.

        Args:
            fps: Current frames per second.

        """
        fps_text = self._small_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
        self._screen.blit(fps_text, (10, 10))

    def render_jamming_status(self, tank: "Tank") -> None:
        """Render jamming cooldown status for perspective tank.

        Args:
            tank: Tank to show jamming status for.

        """
        if not tank.active or not hasattr(tank, "jamming_cooldown"):
            return

        y_offset = 30  # Below FPS counter

        if tank.jamming_active:
            # Show active jamming timer
            status_text = f"JAMMING: {tank.jamming_timer:.1f}s"
            color = (255, 100, 100)  # Red when active
        elif tank.jamming_cooldown > 0:
            # Show cooldown
            status_text = f"Jam Cooldown: {tank.jamming_cooldown:.1f}s"
            color = (150, 150, 150)  # Gray during cooldown
        else:
            # Show ready status
            status_text = "Jam Ready (J)"
            color = (100, 255, 100)  # Green when ready

        text_surface = self._small_font.render(status_text, True, color)
        self._screen.blit(text_surface, (10, y_offset))

    def render_weapon_status(self, tank: "Tank") -> None:
        """Render weapon cooldowns and ammo for perspective tank.

        Args:
            tank: Tank to show weapon status for.

        """
        if not tank.active:
            return

        y_offset = 60  # Below jamming status
        line_height = 20

        # Bullet cooldown
        color = (100, 255, 100) if tank.shoot_cooldown <= 0 else (150, 150, 150)
        bullet_text = (
            "Bullets: Ready (Space)"
            if tank.shoot_cooldown <= 0
            else f"Bullets: {tank.shoot_cooldown:.1f}s"
        )
        text_surface = self._small_font.render(bullet_text, True, color)
        self._screen.blit(text_surface, (10, y_offset))
        y_offset += line_height

        # Missile cooldown
        color = (100, 200, 255) if tank.missile_cooldown <= 0 else (150, 150, 150)
        missile_text = (
            "Missiles: Ready (M)"
            if tank.missile_cooldown <= 0
            else f"Missiles: {tank.missile_cooldown:.1f}s"
        )
        text_surface = self._small_font.render(missile_text, True, color)
        self._screen.blit(text_surface, (10, y_offset))
        y_offset += line_height

        # Mine status
        color = (200, 100, 255) if tank.mine_cooldown <= 0 else (150, 150, 150)
        mine_text = (
            f"Mines: {tank.mine_count}/3 Ready (N)"
            if tank.mine_cooldown <= 0
            else f"Mines: {tank.mine_count}/3 Cooldown {tank.mine_cooldown:.1f}s"
        )
        text_surface = self._small_font.render(mine_text, True, color)
        self._screen.blit(text_surface, (10, y_offset))

    def render_stats_overlay(
        self,
        stats_tracker: "StatsTracker",
        tanks: list["Tank"],
    ) -> None:
        """Render live performance stats overlay.

        Args:
            stats_tracker: Stats tracker with current match stats.
            tanks: List of active tanks to show stats for.

        """
        if not tanks:
            return

        # Position on right side of screen
        x = self._screen.get_width() - 300
        y = 10
        line_height = 20

        # Title
        title_text = self._small_font.render("MATCH STATS", True, (255, 255, 100))
        self._screen.blit(title_text, (x, y))
        y += line_height + 5

        # Stats for each tank
        for tank in tanks:
            stats = stats_tracker.get_stats(tank.id)
            if not stats:
                continue

            # Tank header
            tank_label = f"Tank {tank.id} (Team {tank.team})"
            color = (100, 255, 100) if tank.active else (150, 150, 150)
            header_text = self._small_font.render(tank_label, True, color)
            self._screen.blit(header_text, (x, y))
            y += line_height

            # K/D ratio
            kd_text = f"  K/D: {stats.kills}/{stats.deaths} ({stats.kd_ratio():.2f})"
            text_surface = self._small_font.render(kd_text, True, (200, 200, 200))
            self._screen.blit(text_surface, (x, y))
            y += line_height

            # Accuracy
            acc_text = f"  Acc: {stats.accuracy():.1f}% ({stats.shots_hit}/{stats.shots_fired})"
            text_surface = self._small_font.render(acc_text, True, (200, 200, 200))
            self._screen.blit(text_surface, (x, y))
            y += line_height

            # Damage
            dmg_text = f"  Dmg: {stats.damage_dealt:.0f}D / {stats.damage_taken:.0f}T"
            text_surface = self._small_font.render(dmg_text, True, (200, 200, 200))
            self._screen.blit(text_surface, (x, y))
            y += line_height + 5
