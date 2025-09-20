"""
Player service for the Soccer Coach Sideline Timekeeper application.

This module provides business logic for managing players, including validation,
statistics tracking, attendance management, and player data operations.
"""
import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from src.models.player import (
    Player, ContactInfo, MedicalInfo, PlayerStats, 
    GameAttendance, SkillLevel, DisciplinaryAction
)
from src.services.persistence_service import PersistenceService


class PlayerValidationError(Exception):
    """Custom exception for player validation errors."""
    pass


class PlayerService:
    """
    Service class for managing player data and operations.
    
    Provides methods for player creation, validation, statistics tracking,
    attendance management, and data persistence operations.
    """
    
    # Standard soccer positions
    VALID_POSITIONS = {
        "GK": "Goalkeeper",
        "DF": "Defender", 
        "CB": "Center Back",
        "LB": "Left Back",
        "RB": "Right Back",
        "MF": "Midfielder",
        "CM": "Center Midfielder",
        "LM": "Left Midfielder", 
        "RM": "Right Midfielder",
        "AM": "Attacking Midfielder",
        "DM": "Defensive Midfielder",
        "ST": "Striker",
        "LW": "Left Winger",
        "RW": "Right Winger",
        "CF": "Center Forward"
    }
    
    def __init__(self, persistence_service: Optional[PersistenceService] = None):
        """
        Initialize PlayerService.
        
        Args:
            persistence_service: Optional persistence service instance
        """
        self.persistence_service = persistence_service or PersistenceService()
        
    def validate_player_data(self, player: Player) -> List[str]:
        """
        Validate player data and return list of validation errors.
        
        Args:
            player: Player instance to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Name validation
        if not player.name or not player.name.strip():
            errors.append("Player name is required")
        elif len(player.name.strip()) < 2:
            errors.append("Player name must be at least 2 characters long")
        
        # Number validation
        if player.number and not player.number.isdigit():
            errors.append("Player number must be numeric")
        elif player.number and (int(player.number) < 1 or int(player.number) > 99):
            errors.append("Player number must be between 1 and 99")
        
        # Preferred positions validation
        if player.preferred:
            positions = player.preferred_list()
            invalid_positions = [p for p in positions if p not in self.VALID_POSITIONS]
            if invalid_positions:
                errors.append(f"Invalid positions: {', '.join(invalid_positions)}")
        
        # Age validation (if date_of_birth provided)
        if player.date_of_birth:
            today = date.today()
            if player.date_of_birth > today:
                errors.append("Date of birth cannot be in the future")
            elif player.date_of_birth < date(today.year - 25, today.month, today.day):
                errors.append("Player appears too old for youth soccer (over 25)")
        
        # Skill ratings validation
        for position, rating in player.skill_ratings.items():
            if position not in self.VALID_POSITIONS:
                errors.append(f"Invalid skill rating position: {position}")
            elif not 1 <= rating <= 5:
                errors.append(f"Skill rating for {position} must be between 1 and 5")
        
        # Contact info validation
        if player.contact_info.phone and not self._is_valid_phone(player.contact_info.phone):
            errors.append("Invalid phone number format")
        if player.contact_info.emergency_phone and not self._is_valid_phone(player.contact_info.emergency_phone):
            errors.append("Invalid emergency phone number format")
        if player.contact_info.email and not self._is_valid_email(player.contact_info.email):
            errors.append("Invalid email format")
        
        # Photo path validation
        if player.photo_path and not os.path.exists(player.photo_path):
            errors.append("Photo file does not exist")
        
        return errors
    
    def create_player(
        self,
        name: str,
        number: Optional[str] = None,
        preferred_positions: Optional[List[str]] = None,
        date_of_birth: Optional[date] = None,
        **kwargs
    ) -> Player:
        """
        Create a new player with validation.
        
        Args:
            name: Player's full name
            number: Player's jersey number (optional)
            preferred_positions: List of preferred positions (optional)
            date_of_birth: Player's date of birth (optional)
            **kwargs: Additional player attributes
            
        Returns:
            Validated Player instance
            
        Raises:
            PlayerValidationError: If player data is invalid
        """
        # Create preferred positions string
        preferred = ""
        if preferred_positions:
            preferred = ",".join(pos.upper().strip() for pos in preferred_positions)
        
        # Create player instance
        player = Player(
            name=name.strip(),
            number=number.strip() if number else "",
            preferred=preferred,
            date_of_birth=date_of_birth,
            **kwargs
        )
        
        # Validate player data
        errors = self.validate_player_data(player)
        if errors:
            raise PlayerValidationError(f"Player validation failed: {'; '.join(errors)}")
        
        return player
    
    def update_player_stats(
        self,
        player: Player,
        goals: int = 0,
        assists: int = 0,
        shots: int = 0,
        saves: int = 0,
        fouls_committed: int = 0,
        fouls_received: int = 0,
        yellow_cards: int = 0,
        red_cards: int = 0
    ) -> None:
        """
        Update player statistics for a game.
        
        Args:
            player: Player instance to update
            goals: Goals scored
            assists: Assists made
            shots: Shots taken
            saves: Saves made (for goalkeepers)
            fouls_committed: Fouls committed
            fouls_received: Fouls received
            yellow_cards: Yellow cards received
            red_cards: Red cards received
        """
        stats = player.statistics
        stats.goals += max(0, goals)
        stats.assists += max(0, assists)
        stats.shots += max(0, shots)
        stats.saves += max(0, saves)
        stats.fouls_committed += max(0, fouls_committed)
        stats.fouls_received += max(0, fouls_received)
        stats.yellow_cards += max(0, yellow_cards)
        stats.red_cards += max(0, red_cards)
    
    def record_game_participation(self, player: Player, minutes_played: int, started: bool = False) -> None:
        """
        Record a player's participation in a game.
        
        Args:
            player: Player instance
            minutes_played: Minutes played in the game
            started: Whether the player started the game
        """
        stats = player.statistics
        stats.games_played += 1
        if started:
            stats.games_started += 1
        stats.total_minutes += max(0, minutes_played)
    
    def mark_attendance(self, player: Player, game_date: date, present: bool, reason: Optional[str] = None) -> None:
        """
        Mark player attendance for a specific game date.
        
        Args:
            player: Player instance
            game_date: Date of the game
            present: Whether the player was present
            reason: Reason if absent (optional)
        """
        attendance = GameAttendance(date=game_date, present=present, reason=reason)
        player.add_attendance(attendance)
    
    def get_player_summary(self, player: Player) -> Dict[str, Any]:
        """
        Get comprehensive summary of player information.
        
        Args:
            player: Player instance
            
        Returns:
            Dictionary containing player summary data
        """
        total_minutes = player.total_seconds // 60
        current_stint_minutes = 0
        if player.on_field and player.stint_start_ts:
            current_stint_minutes = player.current_stint_seconds(datetime.now().timestamp()) // 60
        
        return {
            "basic_info": {
                "name": player.name,
                "number": player.number,
                "age": player.age(),
                "preferred_positions": player.preferred_list(),
                "photo_path": player.photo_path,
            },
            "game_status": {
                "on_field": player.on_field,
                "current_position": player.position,
                "total_minutes_played": total_minutes,
                "current_stint_minutes": current_stint_minutes,
            },
            "statistics": {
                "games_played": player.statistics.games_played,
                "games_started": player.statistics.games_started,
                "goals": player.statistics.goals,
                "assists": player.statistics.assists,
                "total_minutes": player.statistics.total_minutes,
                "yellow_cards": player.statistics.yellow_cards,
                "red_cards": player.statistics.red_cards,
            },
            "skill_ratings": {
                position: rating for position, rating in player.skill_ratings.items()
            },
            "attendance": {
                "30_day_rate": player.get_attendance_rate(30),
                "total_records": len(player.attendance_history),
            },
            "contact_available": bool(
                player.contact_info.phone or 
                player.contact_info.email or 
                player.contact_info.emergency_contact
            ),
            "medical_notes": bool(
                player.medical_info.allergies or 
                player.medical_info.medications or 
                player.medical_info.medical_conditions or
                player.medical_info.notes
            ),
        }
    
    def get_position_recommendations(self, player: Player, available_positions: List[str]) -> List[Tuple[str, int]]:
        """
        Get recommended positions for a player based on preferences and skills.
        
        Args:
            player: Player instance
            available_positions: List of positions that need filling
            
        Returns:
            List of (position, score) tuples sorted by recommendation score (higher is better)
        """
        recommendations = []
        
        for position in available_positions:
            score = 0
            
            # Preference bonus (highest priority)
            if position in player.preferred_list():
                score += 50
            
            # Skill rating bonus
            skill_rating = player.get_skill_rating(position)
            score += skill_rating * 10
            
            # Experience bonus (based on statistics)
            if player.statistics.games_played > 0:
                if position == "GK" and player.statistics.saves > 0:
                    score += 20
                elif position in ["ST", "CF", "LW", "RW"] and player.statistics.goals > 0:
                    score += 15
                elif position in ["MF", "AM", "CM"] and player.statistics.assists > 0:
                    score += 15
            
            recommendations.append((position, score))
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
    
    def save_player_photo(self, player: Player, photo_path: str, photos_dir: str = "photos") -> str:
        """
        Save and manage player photo files.
        
        Args:
            player: Player instance
            photo_path: Path to the source photo file
            photos_dir: Directory to store photos (relative to app directory)
            
        Returns:
            Path to the saved photo file
            
        Raises:
            FileNotFoundError: If source photo file doesn't exist
            OSError: If unable to copy photo file
        """
        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Photo file not found: {photo_path}")
        
        # Create photos directory if it doesn't exist
        photos_path = Path(photos_dir)
        photos_path.mkdir(exist_ok=True)
        
        # Generate filename based on player name and current timestamp
        file_extension = Path(photo_path).suffix.lower()
        if not file_extension:
            file_extension = ".jpg"  # Default extension
        
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in player.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}{file_extension}"
        
        destination_path = photos_path / filename
        
        # Copy the photo file
        try:
            shutil.copy2(photo_path, destination_path)
            return str(destination_path)
        except OSError as e:
            raise OSError(f"Unable to save photo: {e}")
    
    def _is_valid_phone(self, phone: str) -> bool:
        """
        Validate phone number format (basic validation).
        
        Args:
            phone: Phone number string
            
        Returns:
            True if phone number appears valid
        """
        if not phone:
            return True  # Empty phone is valid (optional field)
        
        # Remove common separators and spaces
        cleaned = "".join(c for c in phone if c.isdigit())
        
        # Check for reasonable length (7-15 digits)
        return 7 <= len(cleaned) <= 15
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format (basic validation).
        
        Args:
            email: Email address string
            
        Returns:
            True if email appears valid
        """
        if not email:
            return True  # Empty email is valid (optional field)
        
        # Basic email validation
        return "@" in email and "." in email.split("@")[-1] and len(email) >= 5
    
    def export_player_data(self, players: List[Player], filename: str) -> None:
        """
        Export player data to JSON file.
        
        Args:
            players: List of Player instances to export
            filename: Output filename
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "player_count": len(players),
            "players": [player.to_dict() for player in players]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_player_data(self, filename: str) -> List[Player]:
        """
        Import player data from JSON file.
        
        Args:
            filename: Input filename
            
        Returns:
            List of Player instances
            
        Raises:
            FileNotFoundError: If import file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
            PlayerValidationError: If imported data is invalid
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Import file not found: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "players" not in data:
            raise ValueError("Invalid import file format: missing 'players' field")
        
        players = []
        validation_errors = []
        
        for i, player_data in enumerate(data["players"]):
            try:
                player = Player.from_dict(player_data)
                errors = self.validate_player_data(player)
                if errors:
                    validation_errors.append(f"Player {i+1}: {'; '.join(errors)}")
                else:
                    players.append(player)
            except Exception as e:
                validation_errors.append(f"Player {i+1}: Failed to parse - {e}")
        
        if validation_errors:
            error_msg = "Import validation errors:\n" + "\n".join(validation_errors)
            raise PlayerValidationError(error_msg)
        
        return players