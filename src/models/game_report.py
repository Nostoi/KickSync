"""Dataclasses representing analytics reports for the timekeeper app."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlayerTimeSummary:
    """Aggregated playing time information for a single player."""

    name: str
    number: Optional[str]
    preferred_positions: List[str]
    on_field: bool
    position: Optional[str]
    total_seconds: int
    active_stint_seconds: int
    cumulative_seconds: int
    target_seconds: int
    delta_seconds: int
    bench_seconds: int
    target_share: float
    fairness: str


@dataclass
class GameReport:
    """Snapshot of playing time distribution for the current game state."""

    generated_ts: float
    roster_size: int
    regulation_seconds: int
    stoppage_seconds: int
    adjustment_seconds: int
    elapsed_seconds: int
    target_seconds_total: int
    target_seconds_per_player: int
    players: List[PlayerTimeSummary] = field(default_factory=list)
    average_seconds: float = 0.0
    median_seconds: float = 0.0
    min_seconds: int = 0
    max_seconds: int = 0
    fairness_counts: Dict[str, int] = field(default_factory=dict)
