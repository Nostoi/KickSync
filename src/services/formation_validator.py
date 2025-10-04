"""
Formation validation service for ensuring lineup integrity and handling edge cases.

This module provides comprehensive validation for formations, player assignments,
and lineup edge cases following SOLID principles and Clean Code practices.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Protocol
from enum import Enum

from ..models import Player
from ..models.formation import Formation, FieldPosition, Position, FormationType


class ValidationResult:
    """Result of a validation operation with success status and error messages."""
    
    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def add_error(self, error: str) -> None:
        """Add an error message and mark as invalid."""
        self.errors.append(error)
        self.is_valid = False
    
    def combine(self, other: 'ValidationResult') -> 'ValidationResult':
        """Combine with another validation result."""
        result = ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors
        )
        return result


class ValidationRule(ABC):
    """Abstract base class for validation rules following SRP."""
    
    @abstractmethod
    def validate(self, *args, **kwargs) -> ValidationResult:
        """Perform validation and return result."""
        pass


class FormationStructureValidator(ValidationRule):
    """Validates basic formation structure requirements."""
    
    def __init__(self, field_size: int = 11):
        """Initialize with expected field size (7, 9, 10, or 11)."""
        self.field_size = field_size
    
    def validate(self, formation: Formation, field_size: Optional[int] = None) -> ValidationResult:
        """Validate formation structure for specified field size."""
        result = ValidationResult()
        expected_size = field_size if field_size is not None else self.field_size
        
        # Check formation name
        if not formation.name or not formation.name.strip():
            result.add_error("Formation name cannot be empty")
        
        # Check position count (must match field size)
        if len(formation.positions) != expected_size:
            result.add_error(f"Formation must have exactly {expected_size} positions, found {len(formation.positions)}")
        
        # Check for goalkeeper
        gk_positions = [p for p in formation.positions if p.position_code == Position.GOALKEEPER]
        if len(gk_positions) != 1:
            result.add_error(f"Formation must have exactly 1 goalkeeper, found {len(gk_positions)}")
        
        # Check position coordinates are valid (0-100 range)
        for i, pos in enumerate(formation.positions):
            if not (0 <= pos.x <= 100):
                result.add_error(f"Position {i+1} has invalid x coordinate: {pos.x} (must be 0-100)")
            if not (0 <= pos.y <= 100):
                result.add_error(f"Position {i+1} has invalid y coordinate: {pos.y} (must be 0-100)")
        
        return result


class FormationDuplicateValidator(ValidationRule):
    """Validates against duplicate formations and position conflicts."""
    
    def __init__(self, existing_formations: Dict[str, Formation]):
        self.existing_formations = existing_formations
    
    def validate(self, formation: Formation, is_update: bool = False) -> ValidationResult:
        """Validate against duplicates."""
        result = ValidationResult()
        
        # Check for duplicate formation names (unless updating existing)
        if not is_update and formation.name in self.existing_formations:
            result.add_error(f"Formation name '{formation.name}' already exists")
        
        # Check for positions too close together (clustering issue)
        for i, pos1 in enumerate(formation.positions):
            for j, pos2 in enumerate(formation.positions[i+1:], i+1):
                distance = ((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2) ** 0.5
                if distance < 5:  # Minimum distance threshold
                    result.add_error(f"Positions {i+1} and {j+1} are too close together (distance: {distance:.1f})")
        
        return result


class PlayerAssignmentValidator(ValidationRule):
    """Validates player assignments to formation positions."""
    
    def __init__(self, roster: Dict[str, Player]):
        self.roster = roster
    
    def validate(self, formation: Formation, 
                assigned_players: Optional[Dict[str, int]] = None) -> ValidationResult:
        """Validate player assignments."""
        result = ValidationResult()
        
        if assigned_players is None:
            # Extract assignments from formation
            assigned_players = {}
            for pos in formation.positions:
                if pos.player_name:
                    assigned_players[pos.player_name] = pos.player_number or 0
        
        # Check all assigned players exist in roster
        for player_name in assigned_players.keys():
            if player_name not in self.roster:
                result.add_error(f"Player '{player_name}' is not in the roster")
        
        # Check for duplicate player assignments
        seen_players = set()
        for player_name in assigned_players.keys():
            if player_name in seen_players:
                result.add_error(f"Player '{player_name}' is assigned to multiple positions")
            seen_players.add(player_name)
        
        # Check for duplicate jersey numbers
        seen_numbers = set()
        for player_name, number in assigned_players.items():
            if number > 0:  # 0 means no number assigned
                if number in seen_numbers:
                    result.add_error(f"Jersey number {number} is assigned to multiple players")
                seen_numbers.add(number)
                
                # Validate number is in valid range (1-99)
                if not (1 <= number <= 99):
                    result.add_error(f"Invalid jersey number {number} for player '{player_name}' (must be 1-99)")
        
        # Check position suitability (if player has preferred positions)
        for pos in formation.positions:
            if pos.player_name and pos.player_name in self.roster:
                player = self.roster[pos.player_name]
                if player.preferred_positions:
                    preferred_codes = [p.upper() for p in player.preferred_list()]
                    pos_code = pos.position_code.value.upper()
                    
                    # Check if position matches any preferred position
                    position_match = False
                    for pref in preferred_codes:
                        if pref == pos_code or self._positions_compatible(pref, pos_code):
                            position_match = True
                            break
                    
                    if not position_match:
                        result.add_error(
                            f"Player '{pos.player_name}' assigned to {pos_code} "
                            f"but prefers {', '.join(preferred_codes)}"
                        )
        
        return result
    
    def _positions_compatible(self, preferred: str, assigned: str) -> bool:
        """Check if preferred and assigned positions are compatible."""
        # General position compatibility mapping
        compatible_positions = {
            "GK": ["GOALKEEPER"],
            "GOALKEEPER": ["GK"],
            "DEF": ["DEFENDER", "CB", "LB", "RB", "WB"],
            "DEFENDER": ["DEF", "CB", "LB", "RB", "WB"],
            "CB": ["DEFENDER", "DEF"],
            "LB": ["DEFENDER", "DEF", "WB"],
            "RB": ["DEFENDER", "DEF", "WB"],
            "WB": ["LB", "RB", "DEFENDER", "DEF"],
            "MID": ["MIDFIELDER", "CM", "CDM", "CAM", "LM", "RM"],
            "MIDFIELDER": ["MID", "CM", "CDM", "CAM", "LM", "RM"],
            "CM": ["MIDFIELDER", "MID", "CDM", "CAM"],
            "CDM": ["MIDFIELDER", "MID", "CM"],
            "CAM": ["MIDFIELDER", "MID", "CM"],
            "LM": ["MIDFIELDER", "MID", "LW"],
            "RM": ["MIDFIELDER", "MID", "RW"],
            "FOR": ["FORWARD", "ST", "CF", "LW", "RW"],
            "FORWARD": ["FOR", "ST", "CF", "LW", "RW"],
            "ST": ["FORWARD", "FOR", "CF"],
            "CF": ["FORWARD", "FOR", "ST"],
            "LW": ["FOR", "FORWARD", "LM"],
            "RW": ["FOR", "FORWARD", "RM"]
        }
        
        return assigned in compatible_positions.get(preferred, [])


class GameStateValidator(ValidationRule):
    """Validates formation against current game state."""
    
    def __init__(self, is_game_active: bool = False, substitutions_made: int = 0, field_size: int = 11):
        self.is_game_active = is_game_active
        self.substitutions_made = substitutions_made
        self.field_size = field_size
    
    def validate(self, formation: Formation) -> ValidationResult:
        """Validate formation against game state."""
        result = ValidationResult()
        
        # Check if trying to modify formation during active game
        if self.is_game_active:
            result.add_error("Cannot modify formation while game is active")
        
        # Check substitution limits (FIFA allows 5 substitutions in normal play)
        assigned_count = len([p for p in formation.positions if p.player_name])
        if assigned_count < self.field_size and self.substitutions_made >= 5:
            result.add_error("Maximum substitutions reached (5/5)")
        
        return result


class FormationValidationService:
    """
    Comprehensive formation validation service following SOLID principles.
    
    Orchestrates multiple validation rules to ensure formation integrity.
    """
    
    def __init__(self, roster: Dict[str, Player], existing_formations: Dict[str, Formation]):
        self.roster = roster
        self.existing_formations = existing_formations
        
        # Initialize validators
        self.structure_validator = FormationStructureValidator()
        self.duplicate_validator = FormationDuplicateValidator(existing_formations)
        self.assignment_validator = PlayerAssignmentValidator(roster)
    
    def validate_formation(self, formation: Formation, is_update: bool = False,
                          is_game_active: bool = False, substitutions_made: int = 0) -> ValidationResult:
        """
        Perform comprehensive formation validation.
        
        Args:
            formation: Formation to validate
            is_update: Whether this is updating an existing formation
            is_game_active: Whether a game is currently active
            substitutions_made: Number of substitutions already made
            
        Returns:
            ValidationResult with success status and any error messages
        """
        # Combine all validation results
        result = ValidationResult()
        
        # Basic structure validation
        structure_result = self.structure_validator.validate(formation)
        result = result.combine(structure_result)
        
        # Duplicate validation
        duplicate_result = self.duplicate_validator.validate(formation, is_update)
        result = result.combine(duplicate_result)
        
        # Player assignment validation
        assignment_result = self.assignment_validator.validate(formation)
        result = result.combine(assignment_result)
        
        # Game state validation
        game_state_validator = GameStateValidator(is_game_active, substitutions_made)
        game_state_result = game_state_validator.validate(formation)
        result = result.combine(game_state_result)
        
        return result
    
    def validate_player_assignment(self, formation: Formation, position_index: int,
                                 player_name: str, player_number: int) -> ValidationResult:
        """
        Validate a single player assignment to a position.
        
        Args:
            formation: Formation being modified
            position_index: Index of position to assign
            player_name: Name of player to assign
            player_number: Jersey number for player
            
        Returns:
            ValidationResult for the assignment
        """
        result = ValidationResult()
        
        # Check position index is valid
        if not (0 <= position_index < len(formation.positions)):
            result.add_error(f"Invalid position index: {position_index}")
            return result
        
        # Check player exists
        if player_name not in self.roster:
            result.add_error(f"Player '{player_name}' not found in roster")
            return result
        
        # Check player not already assigned elsewhere
        for i, pos in enumerate(formation.positions):
            if i != position_index and pos.player_name == player_name:
                result.add_error(f"Player '{player_name}' is already assigned to position {i+1}")
        
        # Check jersey number not already used
        for i, pos in enumerate(formation.positions):
            if i != position_index and pos.player_number == player_number and player_number > 0:
                result.add_error(f"Jersey number {player_number} is already assigned to position {i+1}")
        
        return result
    
    def get_formation_completeness(self, formation: Formation) -> Tuple[int, int, List[str]]:
        """
        Get formation completeness information.
        
        Returns:
            Tuple of (assigned_positions, total_positions, missing_position_types)
        """
        assigned = len([p for p in formation.positions if p.player_name])
        total = len(formation.positions)
        
        # Check for missing critical position types
        missing_types = []
        position_types = {pos.position_code for pos in formation.positions if pos.player_name}
        
        if Position.GOALKEEPER not in position_types:
            missing_types.append("Goalkeeper")
        
        defender_positions = {Position.DEFENDER, Position.CENTER_BACK, Position.LEFT_BACK, Position.RIGHT_BACK}
        if not any(pos in position_types for pos in defender_positions):
            missing_types.append("Defender")
        
        return assigned, total, missing_types


class LineupEdgeCaseHandler:
    """
    Handler for lineup page edge cases and error scenarios.
    
    Provides user-friendly error messages and recovery suggestions.
    """
    
    def __init__(self, validation_service: FormationValidationService, field_size: int = 11):
        self.validation_service = validation_service
        self.field_size = field_size
    
    def handle_formation_creation_error(self, error_type: str, details: str = "") -> Dict[str, any]:
        """Handle formation creation errors with user-friendly messages."""
        error_messages = {
            "empty_name": "Please enter a formation name before saving.",
            "duplicate_name": f"A formation named '{details}' already exists. Please choose a different name.",
            "invalid_positions": f"Formation must have exactly {self.field_size} positions with 1 goalkeeper.",
            "invalid_coordinates": "Player positions must be within the field boundaries.",
            "network_error": "Unable to save formation. Please check your connection and try again.",
            "permission_error": "Unable to save formation data. Check file permissions."
        }
        
        return {
            "success": False,
            "error": error_messages.get(error_type, f"Formation creation failed: {details}"),
            "error_type": error_type,
            "recovery_suggestions": self._get_recovery_suggestions(error_type)
        }
    
    def handle_player_assignment_error(self, validation_result: ValidationResult) -> Dict[str, any]:
        """Handle player assignment errors with suggestions."""
        if validation_result.is_valid:
            return {"success": True}
        
        return {
            "success": False,
            "errors": validation_result.errors,
            "suggestions": [
                "Check that all players are in your roster",
                "Ensure no player is assigned to multiple positions",
                "Verify jersey numbers are unique and between 1-99",
                "Consider player position preferences for optimal assignments"
            ]
        }
    
    def _get_recovery_suggestions(self, error_type: str) -> List[str]:
        """Get recovery suggestions for specific error types."""
        suggestions = {
            "empty_name": ["Enter a descriptive name for your formation"],
            "duplicate_name": ["Try adding a suffix like '(v2)' or use a different name"],
            "invalid_positions": [
                f"Ensure you have exactly {self.field_size} positions",
                "Check that you have selected 1 goalkeeper",
                "Verify all positions are placed on the field"
            ],
            "network_error": [
                "Check your internet connection",
                "Try refreshing the page and saving again",
                "Contact support if the problem persists"
            ]
        }
        
        return suggestions.get(error_type, ["Please try again or contact support"])