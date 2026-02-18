"""Sound effects and audio management."""

import pygame


class SoundManager:
    """Manages sound effects and audio playback."""

    def __init__(self, enabled: bool = True) -> None:
        """Initialize the sound manager.

        Args:
            enabled: Whether sound effects are enabled.

        """
        self.enabled = enabled
        self.sounds: dict[str, pygame.mixer.Sound | None] = {}

        if self.enabled:
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self._initialize_sounds()
            except pygame.error as e:
                print(f"Warning: Could not initialize sound system: {e}")  # noqa: T201
                self.enabled = False

    def _initialize_sounds(self) -> None:
        """Initialize placeholder sounds.

        This method sets up the sound dictionary with placeholders.
        In a full implementation, this would load actual sound files.

        """
        # Placeholder dictionary - sounds will be loaded from files later
        self.sounds = {
            "shoot": None,  # Tank firing sound
            "hit": None,  # Bullet hitting tank
            "bounce": None,  # Bullet bouncing off wall
            "explosion": None,  # Tank destruction
            "engine": None,  # Tank movement (could be looping)
        }

    def play(self, sound_name: str, volume: float = 1.0) -> None:
        """Play a sound effect.

        Args:
            sound_name: Name of the sound to play.
            volume: Volume level (0.0 to 1.0).

        """
        if not self.enabled:
            return

        sound = self.sounds.get(sound_name)
        if sound:
            sound.set_volume(volume)
            sound.play()
        elif sound_name not in self.sounds:
            # Unknown sound type
            print(f"Warning: Unknown sound '{sound_name}'")  # noqa: T201

    def play_shoot(self) -> None:
        """Play the shooting sound effect."""
        self.play("shoot", volume=0.5)

    def play_hit(self) -> None:
        """Play the bullet hit sound effect."""
        self.play("hit", volume=0.6)

    def play_bounce(self) -> None:
        """Play the bullet bounce sound effect."""
        self.play("bounce", volume=0.4)

    def play_explosion(self) -> None:
        """Play the explosion sound effect."""
        self.play("explosion", volume=0.8)

    def stop_all(self) -> None:
        """Stop all currently playing sounds."""
        if self.enabled:
            pygame.mixer.stop()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable sound effects.

        Args:
            enabled: Whether to enable sound effects.

        """
        self.enabled = enabled
        if not enabled:
            self.stop_all()
