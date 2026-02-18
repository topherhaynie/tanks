"""A fun little game about tanks."""

__version__ = "0.1.0"

from .core import Game
from .entities import Bullet, Tank
from .input import KeyboardController

__all__ = ["Bullet", "Game", "KeyboardController", "Tank"]
