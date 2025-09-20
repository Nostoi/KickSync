"""
GameState model for the Soccer Coach Sideline Timekeeper application.

This module contains the GameState dataclass which represents the complete
state of a soccer game, including players, timing, and persistence methods.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

from .player import Player


@dataclass
class GameState:
    """
    Represents the complete state of a soccer game.
    
    Attributes:
        roster: Dictionary of players keyed by name (unique identifier)
        scheduled_start_ts: Scheduled game start time (epoch seconds)
        game_start_ts: Actual game start time (epoch seconds)
        paused: Whether the game is currently paused
        halftime_started: Whether halftime has begun
        halftime_end_ts: When halftime will end (epoch seconds)
        elapsed_adjustment: Manual time adjustments in seconds
    """
    roster: Dict[str, Player] = field(default_factory=dict)  # key by name (unique)
    # game timing
    scheduled_start_ts: Optional[float] = None
    game_start_ts: Optional[float] = None
    paused: bool = True
    halftime_started: bool = False
    halftime_end_ts: Optional[float] = None
    elapsed_adjustment: int = 0  # manual adjustments if needed

    def to_json(self) -> dict:
        """
        Convert GameState to JSON-serializable dictionary.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "players": {k: asdict(v) for k, v in self.roster.items()},
            "scheduled_start_ts": self.scheduled_start_ts,
            "game_start_ts": self.game_start_ts,
            "paused": self.paused,
            "halftime_started": self.halftime_started,
            "halftime_end_ts": self.halftime_end_ts,
            "elapsed_adjustment": self.elapsed_adjustment,
        }

    @staticmethod
    def from_json(data: dict) -> "GameState":
        """
        Create GameState from JSON dictionary.
        
        Args:
            data: Dictionary with game state data
            
        Returns:
            New GameState instance
        """
        gs = GameState()
        for name, pdata in data.get("players", {}).items():
            p = Player(**{k: pdata.get(k) for k in Player.__dataclass_fields__.keys()})
            gs.roster[name] = p
        gs.scheduled_start_ts = data.get("scheduled_start_ts")
        gs.game_start_ts = data.get("game_start_ts")
        gs.paused = data.get("paused", True)
        gs.halftime_started = data.get("halftime_started", False)
        gs.halftime_end_ts = data.get("halftime_end_ts")
        gs.elapsed_adjustment = int(data.get("elapsed_adjustment", 0))
        return gs