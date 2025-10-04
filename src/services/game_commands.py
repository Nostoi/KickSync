"""
Command pattern implementation for game actions.

This module provides a command pattern implementation for undoable game actions,
following Clean Code principles and supporting undo/redo functionality.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from dataclasses import dataclass
from datetime import datetime

from ..models import GameState, Player
from ..utils import now_ts


class Command(ABC):
    """Abstract base class for all game commands - Command pattern."""
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.
        
        Returns:
            True if command executed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.
        
        Returns:
            True if command undone successfully, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get human-readable description of the command."""
        pass


@dataclass
class GameSnapshot:
    """Immutable snapshot of game state for undo functionality."""
    timestamp: float
    game_start_ts: Optional[float]
    paused: bool
    period_elapsed: List[int]
    current_period_index: int
    player_states: Dict[str, Dict[str, Any]]
    
    @classmethod
    def from_game_state(cls, game_state: GameState) -> 'GameSnapshot':
        """Create snapshot from current game state."""
        player_states = {}
        for name, player in game_state.roster.items():
            player_states[name] = {
                'on_field': player.on_field,
                'position': player.position,
                'total_seconds': player.total_seconds,
                'stint_start_ts': player.stint_start_ts  # Fixed: was 'start_ts'
            }
        
        return cls(
            timestamp=now_ts(),
            game_start_ts=game_state.game_start_ts,
            paused=game_state.paused,
            period_elapsed=game_state.period_elapsed.copy(),
            current_period_index=game_state.current_period_index,
            player_states=player_states
        )


class StartGameCommand(Command):
    """Command to start the game timer."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self._previous_state: Optional[GameSnapshot] = None
    
    def execute(self) -> bool:
        """Start the game timer."""
        try:
            # Ensure timer lists are properly initialized before starting
            self.game_state.ensure_timer_lists()
            
            self._previous_state = GameSnapshot.from_game_state(self.game_state)
            
            if self.game_state.game_start_ts is None:
                self.game_state.game_start_ts = now_ts()
                self.game_state.current_period_index = 0
            
            if self.game_state.period_start_ts is None:
                self.game_state.period_start_ts = now_ts()
            
            self.game_state.paused = False
            return True
            
        except Exception as e:
            # Log the error for debugging
            print(f"ERROR in StartGameCommand.execute(): {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def undo(self) -> bool:
        """Undo game start."""
        if self._previous_state is None:
            return False
        
        try:
            self.game_state.game_start_ts = self._previous_state.game_start_ts
            self.game_state.paused = self._previous_state.paused
            self.game_state.period_elapsed = self._previous_state.period_elapsed.copy()
            self.game_state.current_period_index = self._previous_state.current_period_index
            return True
            
        except Exception:
            return False
    
    @property
    def description(self) -> str:
        return "Start Game"


class PauseGameCommand(Command):
    """Command to pause the game timer."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self._previous_state: Optional[GameSnapshot] = None
    
    def execute(self) -> bool:
        """Pause the game timer."""
        try:
            self._previous_state = GameSnapshot.from_game_state(self.game_state)
            
            if self.game_state.period_start_ts is not None:
                idx = self.game_state.current_period_index
                elapsed = int(now_ts() - self.game_state.period_start_ts)
                self.game_state.period_elapsed[idx] += elapsed
                self.game_state.period_start_ts = None
            
            self.game_state.paused = True
            return True
            
        except Exception:
            return False
    
    def undo(self) -> bool:
        """Undo game pause."""
        if self._previous_state is None:
            return False
        
        try:
            self.game_state.paused = self._previous_state.paused
            self.game_state.period_elapsed = self._previous_state.period_elapsed.copy()
            if not self._previous_state.paused:
                self.game_state.period_start_ts = now_ts()
            return True
            
        except Exception:
            return False
    
    @property
    def description(self) -> str:
        return "Pause Game"


class SubstitutePlayerCommand(Command):
    """Command to substitute players."""
    
    def __init__(self, game_state: GameState, player_out: str, player_in: str):
        self.game_state = game_state
        self.player_out_name = player_out
        self.player_in_name = player_in
        self._previous_state: Optional[GameSnapshot] = None
    
    def execute(self) -> bool:
        """Execute player substitution."""
        try:
            if (self.player_out_name not in self.game_state.roster or
                self.player_in_name not in self.game_state.roster):
                return False
            
            player_out = self.game_state.roster[self.player_out_name]
            player_in = self.game_state.roster[self.player_in_name]
            
            if not player_out.on_field or player_in.on_field:
                return False  # Invalid substitution
            
            self._previous_state = GameSnapshot.from_game_state(self.game_state)
            
            # Record time for outgoing player
            current_time = now_ts()
            if player_out.start_ts is not None:
                player_out.total_seconds += int(current_time - player_out.start_ts)
            
            # Perform substitution
            position = player_out.position
            player_out.on_field = False
            player_out.position = ""
            player_out.start_ts = None
            
            player_in.on_field = True
            player_in.position = position
            player_in.start_ts = current_time
            
            return True
            
        except Exception:
            return False
    
    def undo(self) -> bool:
        """Undo player substitution."""
        if self._previous_state is None:
            return False
        
        try:
            # Restore player states
            player_out = self.game_state.roster[self.player_out_name]
            player_in = self.game_state.roster[self.player_in_name]
            
            out_state = self._previous_state.player_states[self.player_out_name]
            in_state = self._previous_state.player_states[self.player_in_name]
            
            player_out.on_field = out_state['on_field']
            player_out.position = out_state['position']
            player_out.total_seconds = out_state['total_seconds']
            player_out.start_ts = out_state['start_ts']
            
            player_in.on_field = in_state['on_field']
            player_in.position = in_state['position']
            player_in.total_seconds = in_state['total_seconds']
            player_in.start_ts = in_state['start_ts']
            
            return True
            
        except Exception:
            return False
    
    @property
    def description(self) -> str:
        return f"Substitute {self.player_out_name} → {self.player_in_name}"


class GameCommandManager:
    """
    Manager for executing and tracking game commands with undo/redo support.
    
    Follows Command pattern and provides clean interface for game actions.
    """
    
    def __init__(self, max_history: int = 50):
        """
        Initialize command manager.
        
        Args:
            max_history: Maximum number of commands to keep in history
        """
        self.max_history = max_history
        self._command_history: List[Command] = []
        self._current_index = -1
    
    def execute_command(self, command: Command) -> bool:
        """
        Execute a command and add it to history.
        
        Args:
            command: Command to execute
            
        Returns:
            True if command executed successfully
        """
        success = command.execute()
        
        if success:
            # Remove any commands after current index (for redo functionality)
            self._command_history = self._command_history[:self._current_index + 1]
            
            # Add new command
            self._command_history.append(command)
            self._current_index += 1
            
            # Trim history if too long
            if len(self._command_history) > self.max_history:
                self._command_history.pop(0)
                self._current_index -= 1
        
        return success
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            True if undo was successful
        """
        if not self.can_undo():
            return False
        
        command = self._command_history[self._current_index]
        success = command.undo()
        
        if success:
            self._current_index -= 1
        
        return success
    
    def redo(self) -> bool:
        """
        Redo the next command.
        
        Returns:
            True if redo was successful
        """
        if not self.can_redo():
            return False
        
        command = self._command_history[self._current_index + 1]
        success = command.execute()
        
        if success:
            self._current_index += 1
        
        return success
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._current_index >= 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._current_index < len(self._command_history) - 1
    
    def get_command_history(self) -> List[str]:
        """Get history of command descriptions."""
        return [cmd.description for cmd in self._command_history]
    
    def clear_history(self) -> None:
        """Clear command history."""
        self._command_history.clear()
        self._current_index = -1