"""
Player model for the Soccer Coach Sideline Timekeeper application.

This module contains the Player dataclass which represents individual players
and their game state, including playing time tracking, position management,
and enhanced player information.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum


class SkillLevel(Enum):
    """Skill level enumeration for position-specific ratings."""
    BEGINNER = 1
    DEVELOPING = 2
    PROFICIENT = 3
    ADVANCED = 4
    EXPERT = 5


class DisciplinaryAction(Enum):
    """Disciplinary action types."""
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    FOUL = "foul"
    UNSPORTING = "unsporting"


@dataclass
class ContactInfo:
    """Player contact information."""
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "phone": self.phone,
            "email": self.email,
            "emergency_contact": self.emergency_contact,
            "emergency_phone": self.emergency_phone,
            "address": self.address,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'ContactInfo':
        """Create from dictionary for JSON deserialization."""
        if not data:
            return cls()
        return cls(
            phone=data.get("phone"),
            email=data.get("email"),
            emergency_contact=data.get("emergency_contact"),
            emergency_phone=data.get("emergency_phone"),
            address=data.get("address"),
        )


@dataclass
class MedicalInfo:
    """Player medical information."""
    allergies: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    medical_conditions: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    last_physical_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "allergies": self.allergies,
            "medications": self.medications,
            "medical_conditions": self.medical_conditions,
            "notes": self.notes,
            "last_physical_date": self.last_physical_date.isoformat() if self.last_physical_date else None,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'MedicalInfo':
        """Create from dictionary for JSON deserialization."""
        if not data:
            return cls()
        
        last_physical_date = None
        if data.get("last_physical_date"):
            try:
                last_physical_date = date.fromisoformat(data["last_physical_date"])
            except ValueError:
                pass  # Invalid date format, skip
        
        return cls(
            allergies=data.get("allergies", []),
            medications=data.get("medications", []),
            medical_conditions=data.get("medical_conditions", []),
            notes=data.get("notes"),
            last_physical_date=last_physical_date,
        )


@dataclass
class PlayerStats:
    """Player statistics tracking."""
    goals: int = 0
    assists: int = 0
    shots: int = 0
    saves: int = 0  # For goalkeepers
    fouls_committed: int = 0
    fouls_received: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    games_played: int = 0
    games_started: int = 0
    total_minutes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "goals": self.goals,
            "assists": self.assists,
            "shots": self.shots,
            "saves": self.saves,
            "fouls_committed": self.fouls_committed,
            "fouls_received": self.fouls_received,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
            "games_played": self.games_played,
            "games_started": self.games_started,
            "total_minutes": self.total_minutes,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'PlayerStats':
        """Create from dictionary for JSON deserialization."""
        if not data:
            return cls()
        return cls(
            goals=data.get("goals", 0),
            assists=data.get("assists", 0),
            shots=data.get("shots", 0),
            saves=data.get("saves", 0),
            fouls_committed=data.get("fouls_committed", 0),
            fouls_received=data.get("fouls_received", 0),
            yellow_cards=data.get("yellow_cards", 0),
            red_cards=data.get("red_cards", 0),
            games_played=data.get("games_played", 0),
            games_started=data.get("games_started", 0),
            total_minutes=data.get("total_minutes", 0),
        )


@dataclass
class GameAttendance:
    """Game attendance record."""
    date: date
    present: bool
    reason: Optional[str] = None  # Reason if absent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date.isoformat(),
            "present": self.present,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameAttendance':
        """Create from dictionary for JSON deserialization."""
        return cls(
            date=date.fromisoformat(data["date"]),
            present=data["present"],
            reason=data.get("reason"),
        )


@dataclass
class Player:
    """
    Represents a soccer player with playing time tracking, position preferences,
    and enhanced player information including skills, attendance, and statistics.
    
    Attributes:
        # Core fields (backward compatible)
        name: Player's full name (used as unique identifier)
        number: Player's jersey number (optional)
        preferred: Comma-separated preferred positions (e.g., "ST,MF")
        total_seconds: Total playing time accumulated in seconds
        on_field: Whether player is currently on the field
        position: Current field position if on_field is True
        stint_start_ts: Timestamp when current stint started (epoch seconds)
        
        # Enhanced fields (all optional for backward compatibility)
        date_of_birth: Player's date of birth
        photo_path: Path to player's photo file
        contact_info: Contact information
        medical_info: Medical information and notes
        skill_ratings: Position-specific skill ratings (1-5 scale)
        statistics: Player performance statistics
        attendance_history: Game attendance records
        notes: Additional notes about the player
    """
    # Core fields - maintain exact compatibility
    name: str
    number: Optional[str] = ""
    preferred: Optional[str] = ""  # comma-separated e.g. "ST,MF"
    total_seconds: int = 0
    # Runtime fields
    on_field: bool = False
    position: Optional[str] = None
    stint_start_ts: Optional[float] = None  # epoch seconds when last put on field
    
    # Enhanced fields - all optional for backward compatibility
    date_of_birth: Optional[date] = None
    photo_path: Optional[str] = None
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    medical_info: MedicalInfo = field(default_factory=MedicalInfo)
    skill_ratings: Dict[str, int] = field(default_factory=dict)  # position -> skill level (1-5)
    statistics: PlayerStats = field(default_factory=PlayerStats)
    attendance_history: List[GameAttendance] = field(default_factory=list)
    notes: Optional[str] = None

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

    def age(self) -> Optional[int]:
        """
        Calculate player's current age.
        
        Returns:
            Player's age in years, or None if date_of_birth not set
        """
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def get_skill_rating(self, position: str) -> int:
        """
        Get skill rating for a specific position.
        
        Args:
            position: Position code (e.g., "GK", "DF", "MF", "ST")
            
        Returns:
            Skill rating (1-5), defaults to 3 if not set
        """
        return self.skill_ratings.get(position, 3)  # Default to "Proficient"

    def set_skill_rating(self, position: str, rating: int) -> None:
        """
        Set skill rating for a specific position.
        
        Args:
            position: Position code (e.g., "GK", "DF", "MF", "ST")
            rating: Skill rating (1-5)
            
        Raises:
            ValueError: If rating is not between 1 and 5
        """
        if not 1 <= rating <= 5:
            raise ValueError("Skill rating must be between 1 and 5")
        self.skill_ratings[position] = rating

    def add_attendance(self, attendance: GameAttendance) -> None:
        """
        Add a game attendance record.
        
        Args:
            attendance: GameAttendance record to add
        """
        # Remove any existing record for the same date
        self.attendance_history = [
            a for a in self.attendance_history if a.date != attendance.date
        ]
        self.attendance_history.append(attendance)
        # Keep history sorted by date
        self.attendance_history.sort(key=lambda a: a.date, reverse=True)

    def get_attendance_rate(self, days: int = 30) -> float:
        """
        Calculate attendance rate over the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Attendance rate as percentage (0.0-100.0)
        """
        cutoff_date = date.today() - timedelta(days=days)
        recent_attendance = [
            a for a in self.attendance_history if a.date >= cutoff_date
        ]
        
        if not recent_attendance:
            return 100.0  # No records = perfect attendance
        
        present_count = sum(1 for a in recent_attendance if a.present)
        return (present_count / len(recent_attendance)) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert player to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the player
        """
        return {
            # Core fields
            "name": self.name,
            "number": self.number,
            "preferred": self.preferred,
            "total_seconds": self.total_seconds,
            "on_field": self.on_field,
            "position": self.position,
            "stint_start_ts": self.stint_start_ts,
            # Enhanced fields
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "photo_path": self.photo_path,
            "contact_info": self.contact_info.to_dict(),
            "medical_info": self.medical_info.to_dict(),
            "skill_ratings": self.skill_ratings,
            "statistics": self.statistics.to_dict(),
            "attendance_history": [a.to_dict() for a in self.attendance_history],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """
        Create player from dictionary for JSON deserialization.
        
        Args:
            data: Dictionary representation of player
            
        Returns:
            Player instance
        """
        # Handle date_of_birth
        date_of_birth = None
        if data.get("date_of_birth"):
            try:
                date_of_birth = date.fromisoformat(data["date_of_birth"])
            except ValueError:
                pass  # Invalid date format, skip

        # Handle attendance history
        attendance_history = []
        if data.get("attendance_history"):
            for attendance_data in data["attendance_history"]:
                try:
                    attendance_history.append(GameAttendance.from_dict(attendance_data))
                except (ValueError, KeyError):
                    pass  # Invalid attendance data, skip

        return cls(
            # Core fields
            name=data["name"],
            number=data.get("number", ""),
            preferred=data.get("preferred", ""),
            total_seconds=data.get("total_seconds", 0),
            on_field=data.get("on_field", False),
            position=data.get("position"),
            stint_start_ts=data.get("stint_start_ts"),
            # Enhanced fields
            date_of_birth=date_of_birth,
            photo_path=data.get("photo_path"),
            contact_info=ContactInfo.from_dict(data.get("contact_info")),
            medical_info=MedicalInfo.from_dict(data.get("medical_info")),
            skill_ratings=data.get("skill_ratings", {}),
            statistics=PlayerStats.from_dict(data.get("statistics")),
            attendance_history=attendance_history,
            notes=data.get("notes"),
        )