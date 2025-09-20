"""
Player model for the Soccer Coach Sideline Timekeeper application.

This module contains the Player dataclass which represents individual players
and their game state, including playing time tracking and position management.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Player:
    """
    Represents a soccer player with playing time tracking and position preferences.
    
    Attributes:
        name: Player's full name (used as unique identifier)
        number: Player's jersey number (optional)
        preferred: Comma-separated preferred positions (e.g., "ST,MF")
        total_seconds: Total playing time accumulated in seconds
        on_field: Whether player is currently on the field
        position: Current field position if on_field is True
        stint_start_ts: Timestamp when current stint started (epoch seconds)
    """
    name: str
    number: Optional[str] = ""
    preferred: Optional[str] = ""  # comma-separated e.g. "ST,MF"
    total_seconds: int = 0
    # runtime
    on_field: bool = False
    position: Optional[str] = None
    stint_start_ts: Optional[float] = None  # epoch seconds when last put on field

    def start_stint(self, now_ts: float) -> None:
        """
        Start a new playing stint for this player.
        
        Args:
            now_ts: Current timestamp in epoch seconds
        """
        if not self.on_field:
            self.on_field = True
            self.stint_start_ts = now_ts

    def end_stint(self, now_ts: float) -> None:
        """
        End the current playing stint and update total playing time.
        
        Args:
            now_ts: Current timestamp in epoch seconds
        """
        if self.on_field and self.stint_start_ts is not None:
            self.total_seconds += int(now_ts - self.stint_start_ts)
        self.on_field = False
        self.position = None
        self.stint_start_ts = None

    def current_stint_seconds(self, now_ts: float) -> int:
        """
        Calculate seconds played in current stint.
        
        Args:
            now_ts: Current timestamp in epoch seconds
            
        Returns:
            Number of seconds in current stint, or 0 if not on field
        """
        if self.on_field and self.stint_start_ts is not None:
            return int(now_ts - self.stint_start_ts)
        return 0

    def preferred_list(self) -> List[str]:
        """
        Parse preferred positions into a list.
        
        Returns:
            List of preferred position codes (e.g., ["ST", "MF"])
        """
        return [p.strip().upper() for p in (self.preferred or "").split(",") if p.strip()]