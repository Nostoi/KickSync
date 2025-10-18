"""Formation and tactical models for the Soccer Coach Sideline Timekeeper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum


class FormationType(Enum):
    """Standard soccer formation types."""
    F_4_4_2 = "4-4-2"
    F_4_3_3 = "4-3-3"
    F_3_5_2 = "3-5-2"
    F_4_2_3_1 = "4-2-3-1"
    F_3_4_3 = "3-4-3"
    F_5_4_1 = "5-4-1"
    F_4_5_1 = "4-5-1"
    F_5_3_2 = "5-3-2"
    # Smaller field formations
    F_3_3_3 = "3-3-3"  # 10v10
    F_3_2_3 = "3-2-3"  # 9v9
    CUSTOM = "Custom"


class Position(Enum):
    """Player positions on the field."""
    GOALKEEPER = "GK"
    DEFENDER = "DEF"
    MIDFIELDER = "MID"
    FORWARD = "FOR"
    
    # Specific positions
    CENTER_BACK = "CB"
    LEFT_BACK = "LB"
    RIGHT_BACK = "RB"
    WING_BACK = "WB"
    DEFENSIVE_MIDFIELDER = "CDM"
    CENTRAL_MIDFIELDER = "CM"
    ATTACKING_MIDFIELDER = "CAM"
    LEFT_MIDFIELDER = "LM"
    RIGHT_MIDFIELDER = "RM"
    LEFT_WINGER = "LW"
    RIGHT_WINGER = "RW"
    STRIKER = "ST"
    CENTER_FORWARD = "CF"


@dataclass
class FieldPosition:
    """Represents a position on the soccer field with coordinates."""
    x: float  # 0-100, left to right
    y: float  # 0-100, defensive to attacking
    position_code: Position
    player_name: Optional[str] = None
    player_number: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "x": self.x,
            "y": self.y,
            "position_code": self.position_code.value,
            "player_name": self.player_name,
            "player_number": self.player_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> FieldPosition:
        """Create from dictionary."""
        return cls(
            x=data["x"],
            y=data["y"],
            position_code=Position(data["position_code"]),
            player_name=data.get("player_name"),
            player_number=data.get("player_number")
        )


@dataclass
class Formation:
    """Represents a tactical formation with player positions."""
    name: str
    formation_type: FormationType
    positions: List[FieldPosition]
    description: str = ""
    created_at: Optional[datetime] = None
    notes: str = ""
    
    def __post_init__(self):
        """Initialize creation timestamp."""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def get_positions_by_role(self, position_code: Position) -> List[FieldPosition]:
        """Get all field positions for a specific role."""
        return [pos for pos in self.positions if pos.position_code == position_code]
    
    def get_formation_shape(self) -> Tuple[int, int, int, int]:
        """Get formation shape as (GK, DEF, MID, FOR) tuple."""
        gk_count = len([p for p in self.positions if p.position_code == Position.GOALKEEPER])
        
        # Count by general position category
        def_positions = {Position.DEFENDER, Position.CENTER_BACK, Position.LEFT_BACK, 
                        Position.RIGHT_BACK, Position.WING_BACK}
        mid_positions = {Position.MIDFIELDER, Position.DEFENSIVE_MIDFIELDER, 
                        Position.CENTRAL_MIDFIELDER, Position.ATTACKING_MIDFIELDER,
                        Position.LEFT_MIDFIELDER, Position.RIGHT_MIDFIELDER}
        for_positions = {Position.FORWARD, Position.LEFT_WINGER, Position.RIGHT_WINGER,
                        Position.STRIKER, Position.CENTER_FORWARD}
        
        def_count = len([p for p in self.positions if p.position_code in def_positions])
        mid_count = len([p for p in self.positions if p.position_code in mid_positions])
        for_count = len([p for p in self.positions if p.position_code in for_positions])
        
        return (gk_count, def_count, mid_count, for_count)
    
    def assign_player(self, position_index: int, player_name: str, player_number: int) -> None:
        """Assign a player to a specific position."""
        if 0 <= position_index < len(self.positions):
            self.positions[position_index].player_name = player_name
            self.positions[position_index].player_number = player_number
    
    def clear_assignments(self) -> None:
        """Clear all player assignments from the formation."""
        for position in self.positions:
            position.player_name = None
            position.player_number = None
    
    def get_assigned_players(self) -> List[Tuple[str, int, Position]]:
        """Get list of assigned players with their positions."""
        assigned = []
        for pos in self.positions:
            if pos.player_name:
                assigned.append((pos.player_name, pos.player_number or 0, pos.position_code))
        return assigned
    
    def to_dict(self) -> Dict:
        """Convert formation to dictionary for serialization."""
        return {
            "name": self.name,
            "formation_type": self.formation_type.value,
            "positions": [pos.to_dict() for pos in self.positions],
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> Formation:
        """Create formation from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        return cls(
            name=data["name"],
            formation_type=FormationType(data["formation_type"]),
            positions=[FieldPosition.from_dict(pos) for pos in data["positions"]],
            description=data.get("description", ""),
            created_at=created_at,
            notes=data.get("notes", "")
        )


@dataclass
class SubstitutionPlan:
    """Represents a planned substitution strategy."""
    name: str
    substitutions: List[Tuple[str, str, int]]  # (out_player, in_player, target_minute)
    formation_changes: List[Tuple[int, Formation]]  # (minute, new_formation)
    notes: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize creation timestamp."""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def get_substitutions_for_minute(self, minute: int) -> List[Tuple[str, str]]:
        """Get substitutions planned for a specific game minute."""
        return [(out_player, in_player) for out_player, in_player, target_min 
                in self.substitutions if target_min == minute]
    
    def get_formation_for_minute(self, minute: int) -> Optional[Formation]:
        """Get formation change planned for a specific minute."""
        for target_min, formation in self.formation_changes:
            if target_min == minute:
                return formation
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "substitutions": self.substitutions,
            "formation_changes": [(min, form.to_dict()) for min, form in self.formation_changes],
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> SubstitutionPlan:
        """Create from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        formation_changes = []
        for min_val, form_dict in data.get("formation_changes", []):
            formation_changes.append((min_val, Formation.from_dict(form_dict)))
        
        return cls(
            name=data["name"],
            substitutions=data["substitutions"],
            formation_changes=formation_changes,
            notes=data.get("notes", ""),
            created_at=created_at
        )


@dataclass
class OpponentNotes:
    """Stores scouting information about opponents."""
    opponent_name: str
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    key_players: List[str] = field(default_factory=list)
    tactical_notes: str = ""
    recommended_formation: Optional[Formation] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def update_notes(self, **kwargs) -> None:
        """Update opponent notes and timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def add_strength(self, strength: str) -> None:
        """Add a noted strength."""
        if strength and strength not in self.strengths:
            self.strengths.append(strength)
            self.updated_at = datetime.now()
    
    def add_weakness(self, weakness: str) -> None:
        """Add a noted weakness."""
        if weakness and weakness not in self.weaknesses:
            self.weaknesses.append(weakness)
            self.updated_at = datetime.now()
    
    def add_key_player(self, player: str) -> None:
        """Add a key player to watch."""
        if player and player not in self.key_players:
            self.key_players.append(player)
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "opponent_name": self.opponent_name,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "key_players": self.key_players,
            "tactical_notes": self.tactical_notes,
            "recommended_formation": self.recommended_formation.to_dict() if self.recommended_formation else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> OpponentNotes:
        """Create from dictionary."""
        created_at = None
        updated_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        recommended_formation = None
        if data.get("recommended_formation"):
            recommended_formation = Formation.from_dict(data["recommended_formation"])
        
        return cls(
            opponent_name=data["opponent_name"],
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            key_players=data.get("key_players", []),
            tactical_notes=data.get("tactical_notes", ""),
            recommended_formation=recommended_formation,
            created_at=created_at,
            updated_at=updated_at
        )


class FormationTemplates:
    """Pre-defined formation templates for common soccer formations."""
    
    @staticmethod
    def create_4_4_2() -> Formation:
        """Create a 4-4-2 formation template."""
        positions = [
            # Goalkeeper
            FieldPosition(50, 5, Position.GOALKEEPER),
            
            # Defenders
            FieldPosition(20, 20, Position.LEFT_BACK),
            FieldPosition(35, 15, Position.CENTER_BACK),
            FieldPosition(65, 15, Position.CENTER_BACK),
            FieldPosition(80, 20, Position.RIGHT_BACK),
            
            # Midfielders
            FieldPosition(20, 40, Position.LEFT_MIDFIELDER),
            FieldPosition(35, 35, Position.CENTRAL_MIDFIELDER),
            FieldPosition(65, 35, Position.CENTRAL_MIDFIELDER),
            FieldPosition(80, 40, Position.RIGHT_MIDFIELDER),
            
            # Forwards
            FieldPosition(35, 70, Position.STRIKER),
            FieldPosition(65, 70, Position.STRIKER),
        ]
        
        return Formation(
            name="4-4-2 Classic",
            formation_type=FormationType.F_4_4_2,
            positions=positions,
            description="Classic balanced formation with two strikers and solid midfield"
        )
    
    @staticmethod
    def create_4_3_3() -> Formation:
        """Create a 4-3-3 formation template."""
        positions = [
            # Goalkeeper
            FieldPosition(50, 5, Position.GOALKEEPER),
            
            # Defenders
            FieldPosition(20, 20, Position.LEFT_BACK),
            FieldPosition(35, 15, Position.CENTER_BACK),
            FieldPosition(65, 15, Position.CENTER_BACK),
            FieldPosition(80, 20, Position.RIGHT_BACK),
            
            # Midfielders
            FieldPosition(35, 40, Position.CENTRAL_MIDFIELDER),
            FieldPosition(50, 35, Position.CENTRAL_MIDFIELDER),
            FieldPosition(65, 40, Position.CENTRAL_MIDFIELDER),
            
            # Forwards
            FieldPosition(20, 70, Position.LEFT_WINGER),
            FieldPosition(50, 75, Position.STRIKER),
            FieldPosition(80, 70, Position.RIGHT_WINGER),
        ]
        
        return Formation(
            name="4-3-3 Attack",
            formation_type=FormationType.F_4_3_3,
            positions=positions,
            description="Attacking formation with wingers and strong midfield triangle"
        )
    
    @staticmethod
    def create_3_5_2() -> Formation:
        """Create a 3-5-2 formation template."""
        positions = [
            # Goalkeeper
            FieldPosition(50, 5, Position.GOALKEEPER),
            
            # Defenders
            FieldPosition(30, 20, Position.CENTER_BACK),
            FieldPosition(50, 15, Position.CENTER_BACK),
            FieldPosition(70, 20, Position.CENTER_BACK),
            
            # Midfielders
            FieldPosition(15, 45, Position.LEFT_MIDFIELDER),
            FieldPosition(35, 40, Position.CENTRAL_MIDFIELDER),
            FieldPosition(50, 35, Position.CENTRAL_MIDFIELDER),
            FieldPosition(65, 40, Position.CENTRAL_MIDFIELDER),
            FieldPosition(85, 45, Position.RIGHT_MIDFIELDER),
            
            # Forwards
            FieldPosition(40, 70, Position.STRIKER),
            FieldPosition(60, 70, Position.STRIKER),
        ]
        
        return Formation(
            name="3-5-2 Control",
            formation_type=FormationType.F_3_5_2,
            positions=positions,
            description="Midfield-heavy formation with wing play and two strikers"
        )
    
    @staticmethod
    def create_3_3_3() -> Formation:
        """Create a 3-3-3 formation template for 10v10."""
        positions = [
            # Goalkeeper (left side, near left goal)
            FieldPosition(5, 50, Position.GOALKEEPER),
            
            # Defenders (3)
            FieldPosition(22, 25, Position.CENTER_BACK),
            FieldPosition(20, 50, Position.CENTER_BACK),
            FieldPosition(22, 75, Position.CENTER_BACK),
            
            # Midfielders (3)
            FieldPosition(48, 30, Position.CENTRAL_MIDFIELDER),
            FieldPosition(48, 50, Position.CENTRAL_MIDFIELDER),
            FieldPosition(48, 70, Position.CENTRAL_MIDFIELDER),
            
            # Forwards (3)
            FieldPosition(78, 25, Position.LEFT_WINGER),
            FieldPosition(82, 50, Position.STRIKER),
            FieldPosition(78, 75, Position.RIGHT_WINGER),
        ]
        
        return Formation(
            name="3-3-3 Balanced (10v10)",
            formation_type=FormationType.F_3_3_3,
            positions=positions,
            description="Balanced 10v10 formation with equal distribution across defense, midfield, and attack"
        )
    
    @staticmethod
    def create_3_2_3() -> Formation:
        """Create a 3-2-3 formation template for 9v9."""
        positions = [
            # Goalkeeper (left side, near left goal)
            FieldPosition(5, 50, Position.GOALKEEPER),
            
            # Defenders (3)
            FieldPosition(22, 25, Position.CENTER_BACK),
            FieldPosition(20, 50, Position.CENTER_BACK),
            FieldPosition(22, 75, Position.CENTER_BACK),
            
            # Midfielders (2)
            FieldPosition(48, 35, Position.CENTRAL_MIDFIELDER),
            FieldPosition(48, 65, Position.CENTRAL_MIDFIELDER),
            
            # Forwards (3)
            FieldPosition(78, 25, Position.LEFT_WINGER),
            FieldPosition(82, 50, Position.STRIKER),
            FieldPosition(78, 75, Position.RIGHT_WINGER),
        ]
        
        return Formation(
            name="3-2-3 Attack (9v9)",
            formation_type=FormationType.F_3_2_3,
            positions=positions,
            description="Attacking 9v9 formation with strong defensive line and three forwards"
        )
    
    @staticmethod
    def get_all_templates() -> List[Formation]:
        """Get all pre-defined formation templates."""
        return [
            FormationTemplates.create_4_4_2(),
            FormationTemplates.create_4_3_3(),
            FormationTemplates.create_3_5_2(),
            FormationTemplates.create_3_3_3(),  # 10v10
            FormationTemplates.create_3_2_3(),  # 9v9
        ]
    
    @staticmethod
    def get_template_by_type(formation_type: FormationType) -> Optional[Formation]:
        """Get template by formation type."""
        templates = {
            FormationType.F_4_4_2: FormationTemplates.create_4_4_2,
            FormationType.F_4_3_3: FormationTemplates.create_4_3_3,
            FormationType.F_3_5_2: FormationTemplates.create_3_5_2,
            FormationType.F_3_3_3: FormationTemplates.create_3_3_3,
            FormationType.F_3_2_3: FormationTemplates.create_3_2_3,
        }
        
        factory = templates.get(formation_type)
        return factory() if factory else None