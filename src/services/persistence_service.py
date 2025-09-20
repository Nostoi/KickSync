"""
Persistence service for the Soccer Coach Sideline Timekeeper application.

This module handles saving and loading game state to/from JSON files.
"""
import json
import os
from typing import Optional

from ..models import GameState
from ..utils import now_ts


class PersistenceService:
    """
    Service for persisting game state to JSON files.
    
    This service handles the complexities of saving live game state,
    including capturing current stint data without ending active stints.
    """

    @staticmethod
    def save_game_to_file(game_state: GameState, file_path: str) -> None:
        """
        Save game state to a JSON file.
        
        Args:
            game_state: The game state to save
            file_path: Path where to save the file
            
        Raises:
            IOError: If file cannot be written
            OSError: If path is invalid
        """
        # Create snapshot that captures current live totals without ending stints
        snapshot = PersistenceService._create_snapshot_for_save(game_state)
        
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    @staticmethod
    def load_game_from_file(file_path: str) -> GameState:
        """
        Load game state from a JSON file.
        
        Args:
            file_path: Path to the JSON file to load
            
        Returns:
            GameState instance loaded from file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
            ValueError: If JSON structure is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Game file not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return GameState.from_json(data)

    @staticmethod
    def _create_snapshot_for_save(game_state: GameState) -> dict:
        """
        Create a snapshot of game state suitable for saving.
        
        This captures current playing time without ending active stints,
        so the game can continue after loading.
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        # Create a copy to avoid modifying the original
        temp = GameState.from_json(game_state.to_json())
        current_time = now_ts()
        
        # Add current stint seconds to total without ending stints
        for player in temp.roster.values():
            if player.on_field and player.stint_start_ts is not None:
                player.total_seconds += player.current_stint_seconds(current_time)
                # Keep stint_start_ts for live tracking after load
                
        return temp.to_json()

    @staticmethod
    def auto_save(game_state: GameState, auto_save_dir: str = "autosave") -> Optional[str]:
        """
        Automatically save game state with timestamp.
        
        Args:
            game_state: Game state to save
            auto_save_dir: Directory for auto-save files
            
        Returns:
            Path to saved file, or None if save failed
        """
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"game_autosave_{timestamp}.json"
            file_path = os.path.join(auto_save_dir, filename)
            
            PersistenceService.save_game_to_file(game_state, file_path)
            return file_path
        except Exception:
            # Auto-save should not crash the application
            return None

    @staticmethod
    def get_recent_saves(save_dir: str = ".", limit: int = 10) -> list:
        """
        Get list of recent save files.
        
        Args:
            save_dir: Directory to search for save files
            limit: Maximum number of files to return
            
        Returns:
            List of tuples (filename, modification_time) sorted by newest first
        """
        if not os.path.exists(save_dir):
            return []
            
        try:
            json_files = []
            for filename in os.listdir(save_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(save_dir, filename)
                    if os.path.isfile(file_path):
                        mtime = os.path.getmtime(file_path)
                        json_files.append((filename, mtime))
                        
            # Sort by modification time, newest first
            json_files.sort(key=lambda x: x[1], reverse=True)
            return json_files[:limit]
        except OSError:
            return []