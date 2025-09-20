"""
GameState model for the Soccer Coach Sideline Timekeeper application.

This module contains the GameState dataclass which represents the complete
state of a soccer game, including players, timing, and persistence methods.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from .player import Player
from ..utils import DEFAULT_GAME_LENGTH_MIN, DEFAULT_PERIOD_COUNT


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
        elapsed_adjustment: Manual time adjustments in seconds (legacy aggregate)
        game_length_seconds: Configured regulation game length (without stoppage)
        period_count: Number of regulation periods in the game
        period_elapsed: Accumulated regulation seconds played per period
        period_adjustments: Manual adjustments applied per period
        period_stoppage: Stoppage/injury time tracked per period
        current_period_index: Index of active period (0-based)
        period_start_ts: Epoch timestamp when the current period started/resumed
    """
    roster: Dict[str, Player] = field(default_factory=dict)  # key by name (unique)
    # game timing
    scheduled_start_ts: Optional[float] = None
    game_start_ts: Optional[float] = None
    paused: bool = True
    halftime_started: bool = False
    halftime_end_ts: Optional[float] = None
    elapsed_adjustment: int = 0  # manual adjustments if needed
    game_length_seconds: int = DEFAULT_GAME_LENGTH_MIN * 60
    period_count: int = DEFAULT_PERIOD_COUNT
    period_elapsed: List[int] = field(default_factory=list)
    period_adjustments: List[int] = field(default_factory=list)
    period_stoppage: List[int] = field(default_factory=list)
    current_period_index: int = 0
    period_start_ts: Optional[float] = None

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
            "game_length_seconds": self.game_length_seconds,
            "period_count": self.period_count,
            "period_elapsed": list(self.period_elapsed),
            "period_adjustments": list(self.period_adjustments),
            "period_stoppage": list(self.period_stoppage),
            "current_period_index": self.current_period_index,
            "period_start_ts": self.period_start_ts,
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
        legacy_adjustment = int(data.get("elapsed_adjustment", 0))
        gs.elapsed_adjustment = legacy_adjustment

        gs.game_length_seconds = int(
            data.get(
                "game_length_seconds",
                int(data.get("game_length_min", DEFAULT_GAME_LENGTH_MIN)) * 60,
            )
        )
        gs.period_count = max(1, int(data.get("period_count", DEFAULT_PERIOD_COUNT)))

        def _to_int_list(key: str) -> List[int]:
            raw = data.get(key, []) or []
            return [int(value) for value in raw]

        gs.period_elapsed = _to_int_list("period_elapsed")
        gs.period_adjustments = _to_int_list("period_adjustments")
        gs.period_stoppage = _to_int_list("period_stoppage")

        # Backward compatibility – older saves only tracked aggregate adjustments
        if not gs.period_adjustments and legacy_adjustment:
            gs.period_adjustments = [legacy_adjustment]

        gs.current_period_index = int(data.get("current_period_index", 0))
        gs.period_start_ts = data.get("period_start_ts")

        gs.ensure_timer_lists()
        # Keep aggregate adjustment in sync with per-period values
        gs.elapsed_adjustment = sum(gs.period_adjustments[: gs.period_count])
        return gs

    def ensure_timer_lists(self) -> None:
        """Ensure period-related lists match the configured period count."""

        self.period_count = max(1, self.period_count)

        def _normalize_list(values: List[int]) -> List[int]:
            if len(values) < self.period_count:
                values = values + [0] * (self.period_count - len(values))
            elif len(values) > self.period_count:
                values = values[: self.period_count]
            return values

        self.period_elapsed = _normalize_list(self.period_elapsed)
        self.period_adjustments = _normalize_list(self.period_adjustments)
        self.period_stoppage = _normalize_list(self.period_stoppage)

        if self.current_period_index >= self.period_count:
            self.current_period_index = self.period_count - 1

        # Ensure timer fields are non-negative integers where applicable
        self.game_length_seconds = max(60, int(self.game_length_seconds or 0))