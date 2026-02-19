"""Bot system for AI players."""

from tanks.bots.bot_api import Bot, BotAction, BotState
from tanks.bots.bot_controller import BotController
from tanks.bots.external_controller import ExternalBotController
from tanks.bots.external_runner import ExternalBotRunner
from tanks.bots.simple_bot import SimpleBot
from tanks.bots.smart_bot import SmartBot

__all__ = [
    "Bot",
    "BotAction",
    "BotController",
    "BotState",
    "ExternalBotController",
    "ExternalBotRunner",
    "SimpleBot",
    "SmartBot",
]
