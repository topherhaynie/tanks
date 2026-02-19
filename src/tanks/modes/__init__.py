"""Game modes (duel, arena, tournament, level)."""

from tanks.modes.arena import ArenaConfig, ArenaSize, ArenaStats
from tanks.modes.arena_setup import ArenaSetup
from tanks.modes.match import Match, MatchResult, MatchStatus
from tanks.modes.tournament import TankRanking, Tournament, TournamentFormat
from tanks.modes.win_condition import WinCondition, WinConditionType

__all__ = [
    "ArenaConfig",
    "ArenaSetup",
    "ArenaSize",
    "ArenaStats",
    "Match",
    "MatchResult",
    "MatchStatus",
    "TankRanking",
    "Tournament",
    "TournamentFormat",
    "WinCondition",
    "WinConditionType",
]
