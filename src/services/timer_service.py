"""
Timer service for the Soccer Coach Sideline Timekeeper application.

This module handles game timing logic, including start/pause/resume functionality
and halftime management.
"""
from typing import Optional, Tuple
from ..models import GameState
from ..utils import now_ts, GAME_LENGTH_MIN, HALFTIME_PAUSE_MIN


class TimerService:
    """
    Service for managing game timing and state transitions.
    
    This service handles the complexities of soccer game timing including
    regular time, halftime, and manual adjustments.
    """

    def __init__(self, game_state: GameState):
        """
        Initialize timer service with game state.
        
        Args:
            game_state: The game state to manage
        """
        self.game_state = game_state

    def start_game(self) -> None:
        """
        Start the game timer.
        
        Sets the game start time if not already set and unpauses the game.
        Resumes any active player stints that were paused.
        """
        if self.game_state.game_start_ts is None:
            self.game_state.game_start_ts = now_ts()
        self.game_state.paused = False

    def pause_game(self) -> None:
        """
        Pause the game timer.
        
        Player stints continue to track but game time stops.
        """
        self.game_state.paused = True

    def resume_game(self) -> None:
        """
        Resume the game timer.
        
        Continues game timing from where it was paused.
        """
        self.game_state.paused = False

    def reset_game(self) -> None:
        """
        Reset the game to initial state.
        
        Clears all timing data and returns to pre-game state.
        """
        self.game_state.game_start_ts = None
        self.game_state.scheduled_start_ts = None
        self.game_state.paused = True
        self.game_state.halftime_started = False
        self.game_state.halftime_end_ts = None
        self.game_state.elapsed_adjustment = 0

    def start_halftime(self) -> None:
        """
        Begin halftime period.
        
        Sets halftime flag and calculates when halftime should end.
        """
        current_time = now_ts()
        self.game_state.halftime_started = True
        self.game_state.halftime_end_ts = current_time + (HALFTIME_PAUSE_MIN * 60)
        self.game_state.paused = True

    def end_halftime(self) -> None:
        """
        End halftime period and resume the game.
        
        Clears halftime flags and resumes game timing.
        """
        self.game_state.halftime_started = False
        self.game_state.halftime_end_ts = None
        self.game_state.paused = False

    def add_time_adjustment(self, seconds: int) -> None:
        """
        Add manual time adjustment (stoppage time, corrections).
        
        Args:
            seconds: Seconds to add (can be negative for corrections)
        """
        self.game_state.elapsed_adjustment += seconds

    def get_game_elapsed_seconds(self) -> int:
        """
        Get total elapsed game time in seconds.
        
        Returns:
            Elapsed seconds including adjustments, or 0 if game not started
        """
        if self.game_state.game_start_ts is None:
            return 0

        current_time = now_ts()
        elapsed = int(current_time - self.game_state.game_start_ts)
        
        # Add manual adjustments
        elapsed += self.game_state.elapsed_adjustment
        
        return max(0, elapsed)  # Never negative

    def get_remaining_seconds(self) -> int:
        """
        Get remaining game time in seconds.
        
        Returns:
            Remaining seconds, or full game length if not started
        """
        total_game_seconds = GAME_LENGTH_MIN * 60
        elapsed = self.get_game_elapsed_seconds()
        return max(0, total_game_seconds - elapsed)

    def is_game_over(self) -> bool:
        """
        Check if game time has expired.
        
        Returns:
            True if game time has elapsed
        """
        return self.get_remaining_seconds() == 0

    def get_half_info(self) -> Tuple[int, bool]:
        """
        Get current half information.
        
        Returns:
            Tuple of (current_half, is_halftime)
            current_half: 1 or 2
            is_halftime: True if currently in halftime break
        """
        if self.game_state.halftime_started:
            return (1, True)
        
        elapsed = self.get_game_elapsed_seconds()
        half_time_seconds = (GAME_LENGTH_MIN * 60) // 2
        
        if elapsed <= half_time_seconds:
            return (1, False)
        else:
            return (2, False)

    def should_suggest_halftime(self) -> bool:
        """
        Check if halftime should be suggested based on elapsed time.
        
        Returns:
            True if first half is complete and halftime hasn't started
        """
        if self.game_state.halftime_started:
            return False
            
        elapsed = self.get_game_elapsed_seconds()
        half_time_seconds = (GAME_LENGTH_MIN * 60) // 2
        
        return elapsed >= half_time_seconds

    def get_halftime_remaining_seconds(self) -> Optional[int]:
        """
        Get remaining halftime seconds.
        
        Returns:
            Remaining halftime seconds, or None if not in halftime
        """
        if not self.game_state.halftime_started or self.game_state.halftime_end_ts is None:
            return None
            
        current_time = now_ts()
        remaining = int(self.game_state.halftime_end_ts - current_time)
        return max(0, remaining)

    def is_halftime_over(self) -> bool:
        """
        Check if halftime period has expired.
        
        Returns:
            True if halftime time has elapsed
        """
        remaining = self.get_halftime_remaining_seconds()
        return remaining is not None and remaining == 0