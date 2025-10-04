"""Strategy service for team formation, substitution planning, and tactical analysis."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..models import GameState, Player
from ..models.formation import (
    Formation, FormationTemplates, FormationType, FieldPosition, Position,
    SubstitutionPlan, OpponentNotes
)


class StrategyService:
    """
    Manages team strategy including formations, substitution plans, and opponent scouting.
    """
    
    def __init__(self, game_state: GameState, formations_file: Optional[str] = None):
        """
        Initialize the strategy service.
        
        Args:
            game_state: Current game state with players
            formations_file: Optional path to formations data file
        """
        self.game_state = game_state
        self.formations_file = formations_file or "formations.json"
        
        # In-memory storage
        self._formations: Dict[str, Formation] = {}
        self._substitution_plans: Dict[str, SubstitutionPlan] = {}
        self._opponent_notes: Dict[str, OpponentNotes] = {}
        
        # Load existing data
        self._load_data()
    
    # ---------- Formation Management ---------- #
    
    def create_formation(self, name: str, formation_type: FormationType, 
                        positions: List[FieldPosition], description: str = "") -> Formation:
        """
        Create a new formation.
        
        Args:
            name: Formation name
            formation_type: Type of formation
            positions: List of field positions
            description: Optional description
            
        Returns:
            Created formation
        """
        formation = Formation(
            name=name,
            formation_type=formation_type,
            positions=positions,
            description=description
        )
        
        self._formations[name] = formation
        self._save_data()
        return formation
    
    def get_formation(self, name: str) -> Optional[Formation]:
        """Get formation by name."""
        return self._formations.get(name)
    
    def list_formations(self) -> List[Formation]:
        """Get all available formations."""
        return list(self._formations.values())
    
    def delete_formation(self, name: str) -> bool:
        """Delete a formation."""
        if name in self._formations:
            del self._formations[name]
            self._save_data()
            return True
        return False
    
    def get_formation_templates(self) -> List[Formation]:
        """Get pre-defined formation templates."""
        return FormationTemplates.get_all_templates()
    
    def create_from_template(self, template_type: FormationType, name: str) -> Optional[Formation]:
        """Create formation from template."""
        template = FormationTemplates.get_template_by_type(template_type)
        if template:
            template.name = name
            self._formations[name] = template
            self._save_data()
            return template
        return None
    
    # ---------- Player Assignment and Rotation ---------- #
    
    def assign_players_to_formation(self, formation: Formation, 
                                  player_assignments: Dict[int, str]) -> Formation:
        """
        Assign players to formation positions.
        
        Args:
            formation: Formation to assign players to
            player_assignments: Dict mapping position_index -> player_name
            
        Returns:
            Updated formation
        """
        formation.clear_assignments()
        
        for position_idx, player_name in player_assignments.items():
            if player_name in self.game_state.roster:
                player = self.game_state.roster[player_name]
                formation.assign_player(position_idx, player.name, player.number)
        
        return formation
    
    def suggest_optimal_formation(self, available_players: List[Player]) -> Optional[Formation]:
        """
        Suggest optimal formation based on available players and their positions.
        
        Args:
            available_players: List of available players
            
        Returns:
            Recommended formation or None if can't determine
        """
        if len(available_players) < 11:
            return None
        
        # Count players by preferred position
        position_counts = {}
        for player in available_players:
            preferred = player.preferred_list()
            for pos in preferred:
                if pos.upper() in ["GK", "GOALKEEPER"]:
                    position_counts["GK"] = position_counts.get("GK", 0) + 1
                elif pos.upper() in ["DEF", "DEFENDER", "CB", "LB", "RB"]:
                    position_counts["DEF"] = position_counts.get("DEF", 0) + 1
                elif pos.upper() in ["MID", "MIDFIELDER", "CM", "CDM", "CAM", "LM", "RM"]:
                    position_counts["MID"] = position_counts.get("MID", 0) + 1
                elif pos.upper() in ["FOR", "FORWARD", "ST", "LW", "RW", "CF"]:
                    position_counts["FOR"] = position_counts.get("FOR", 0) + 1
        
        # Suggest formation based on player distribution
        def_count = position_counts.get("DEF", 0)
        mid_count = position_counts.get("MID", 0)
        for_count = position_counts.get("FOR", 0)
        
        if def_count >= 4 and mid_count >= 4 and for_count >= 2:
            return FormationTemplates.create_4_4_2()
        elif def_count >= 4 and mid_count >= 3 and for_count >= 3:
            return FormationTemplates.create_4_3_3()
        elif def_count >= 3 and mid_count >= 5 and for_count >= 2:
            return FormationTemplates.create_3_5_2()
        else:
            # Default to 4-4-2
            return FormationTemplates.create_4_4_2()
    
    def suggest_position_rotations(self, current_formation: Formation, 
                                 available_players: List[Player]) -> List[Tuple[str, str, Position]]:
        """
        Suggest position rotations based on player skills and fatigue.
        
        Args:
            current_formation: Current formation with assignments
            available_players: Available players for rotation
            
        Returns:
            List of (out_player, in_player, position) suggestions
        """
        suggestions = []
        assigned_players = {pos.player_name for pos in current_formation.positions if pos.player_name}
        bench_players = [p for p in available_players if p.name not in assigned_players]
        
        if not bench_players:
            return suggestions
        
        # Simple rotation logic based on playing time
        for position in current_formation.positions:
            if position.player_name and position.player_name in self.game_state.roster:
                current_player = self.game_state.roster[position.player_name]
                
                # Consider rotation if player has played more than 45 minutes
                if current_player.total_seconds > 2700:  # 45 minutes
                    # Find suitable replacement
                    suitable_replacements = []
                    for bench_player in bench_players:
                        preferred = bench_player.preferred_list()
                        if any(pos.upper() in position.position_code.value.upper() for pos in preferred):
                            suitable_replacements.append(bench_player)
                    
                    if suitable_replacements:
                        # Pick the freshest player (least playing time)
                        replacement = min(suitable_replacements, key=lambda p: p.total_seconds)
                        suggestions.append((current_player.name, replacement.name, position.position_code))
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    # ---------- Substitution Planning ---------- #
    
    def create_substitution_plan(self, name: str, substitutions: List[Tuple[str, str, int]] = None,
                               formation_changes: List[Tuple[int, Formation]] = None) -> SubstitutionPlan:
        """Create a new substitution plan."""
        plan = SubstitutionPlan(
            name=name,
            substitutions=substitutions or [],
            formation_changes=formation_changes or []
        )
        
        self._substitution_plans[name] = plan
        self._save_data()
        return plan
    
    def get_substitution_plan(self, name: str) -> Optional[SubstitutionPlan]:
        """Get substitution plan by name."""
        return self._substitution_plans.get(name)
    
    def list_substitution_plans(self) -> List[SubstitutionPlan]:
        """Get all substitution plans."""
        return list(self._substitution_plans.values())
    
    def generate_smart_substitution_plan(self, formation: Formation, 
                                       game_length_minutes: int = 60) -> SubstitutionPlan:
        """
        Generate intelligent substitution plan based on formation and game length.
        
        Args:
            formation: Starting formation
            game_length_minutes: Total game length
            
        Returns:
            Generated substitution plan
        """
        substitutions = []
        formation_changes = []
        
        # Get all available players
        all_players = list(self.game_state.roster.values())
        assigned_players = {pos.player_name for pos in formation.positions if pos.player_name}
        bench_players = [p for p in all_players if p.name not in assigned_players]
        
        if not bench_players:
            return self.create_substitution_plan("Auto-Generated Plan (No Bench)")
        
        # Plan substitutions at key intervals
        substitution_times = []
        if game_length_minutes >= 45:
            substitution_times = [25, 35, 45]  # For longer games
        elif game_length_minutes >= 30:
            substitution_times = [20, 30]  # For medium games
        else:
            substitution_times = [15]  # For short games
        
        bench_index = 0
        for sub_time in substitution_times:
            if bench_index >= len(bench_players):
                break
            
            # Find a player to substitute (prioritize those who have played most)
            field_players = [pos for pos in formation.positions if pos.player_name and pos.position_code != Position.GOALKEEPER]
            if field_players:
                # Simple rotation: substitute a random field player
                target_position = random.choice(field_players)
                if target_position.player_name:
                    substitutions.append((
                        target_position.player_name,
                        bench_players[bench_index].name,
                        sub_time
                    ))
                    bench_index += 1
        
        plan_name = f"Auto Plan - {formation.name}"
        return self.create_substitution_plan(plan_name, substitutions, formation_changes)
    
    # ---------- Opponent Scouting ---------- #
    
    def create_opponent_notes(self, opponent_name: str) -> OpponentNotes:
        """Create new opponent scouting notes."""
        notes = OpponentNotes(opponent_name=opponent_name)
        self._opponent_notes[opponent_name] = notes
        self._save_data()
        return notes
    
    def get_opponent_notes(self, opponent_name: str) -> Optional[OpponentNotes]:
        """Get opponent notes by name."""
        return self._opponent_notes.get(opponent_name)
    
    def update_opponent_notes(self, opponent_name: str, **updates) -> Optional[OpponentNotes]:
        """Update opponent notes."""
        notes = self._opponent_notes.get(opponent_name)
        if notes:
            notes.update_notes(**updates)
            self._save_data()
        return notes
    
    def list_opponent_notes(self) -> List[OpponentNotes]:
        """Get all opponent notes."""
        return list(self._opponent_notes.values())
    
    def recommend_counter_formation(self, opponent_notes: OpponentNotes) -> Optional[Formation]:
        """
        Recommend formation to counter opponent's tactics.
        
        Args:
            opponent_notes: Opponent scouting information
            
        Returns:
            Recommended counter-formation
        """
        if opponent_notes.recommended_formation:
            opponent_formation = opponent_notes.recommended_formation
            opponent_shape = opponent_formation.get_formation_shape()
            
            # Simple counter-formation logic
            _, opp_def, opp_mid, opp_for = opponent_shape
            
            # If opponent is defensive (5+ defenders), use attacking formation
            if opp_def >= 5:
                return FormationTemplates.create_4_3_3()  # More attacking
            
            # If opponent has strong midfield (5+ midfielders), match it
            elif opp_mid >= 5:
                return FormationTemplates.create_3_5_2()  # Strong midfield
            
            # If opponent is attacking (3+ forwards), strengthen defense
            elif opp_for >= 3:
                return FormationTemplates.create_4_4_2()  # Balanced defense
        
        # Default recommendation
        return FormationTemplates.create_4_4_2()
    
    # ---------- Data Persistence ---------- #
    
    def _save_data(self) -> None:
        """Save all strategy data to file."""
        try:
            data = {
                "formations": {name: formation.to_dict() for name, formation in self._formations.items()},
                "substitution_plans": {name: plan.to_dict() for name, plan in self._substitution_plans.items()},
                "opponent_notes": {name: notes.to_dict() for name, notes in self._opponent_notes.items()}
            }
            
            with open(self.formations_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"Warning: Failed to save strategy data: {e}")
    
    def _load_data(self) -> None:
        """Load strategy data from file."""
        try:
            if Path(self.formations_file).exists():
                with open(self.formations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load formations
                for name, formation_data in data.get("formations", {}).items():
                    try:
                        self._formations[name] = Formation.from_dict(formation_data)
                    except Exception as e:
                        print(f"Warning: Failed to load formation '{name}': {e}")
                
                # Load substitution plans
                for name, plan_data in data.get("substitution_plans", {}).items():
                    try:
                        self._substitution_plans[name] = SubstitutionPlan.from_dict(plan_data)
                    except Exception as e:
                        print(f"Warning: Failed to load substitution plan '{name}': {e}")
                
                # Load opponent notes
                for name, notes_data in data.get("opponent_notes", {}).items():
                    try:
                        self._opponent_notes[name] = OpponentNotes.from_dict(notes_data)
                    except Exception as e:
                        print(f"Warning: Failed to load opponent notes '{name}': {e}")
        
        except Exception as e:
            print(f"Warning: Failed to load strategy data: {e}")
    
    # ---------- Analytics and Reporting ---------- #
    
    def get_formation_usage_stats(self) -> Dict[str, int]:
        """Get statistics on formation usage."""
        usage_stats = {}
        for formation in self._formations.values():
            formation_type = formation.formation_type.value
            usage_stats[formation_type] = usage_stats.get(formation_type, 0) + 1
        return usage_stats
    
    def get_substitution_patterns(self) -> Dict[str, List[int]]:
        """Analyze substitution timing patterns."""
        patterns = {}
        for plan in self._substitution_plans.values():
            for _, _, minute in plan.substitutions:
                if plan.name not in patterns:
                    patterns[plan.name] = []
                patterns[plan.name].append(minute)
        return patterns
    
    def export_strategy_summary(self) -> Dict:
        """Export comprehensive strategy summary."""
        return {
            "formations": {
                "total": len(self._formations),
                "types": self.get_formation_usage_stats(),
                "custom_formations": [f.name for f in self._formations.values() if f.formation_type == FormationType.CUSTOM]
            },
            "substitution_plans": {
                "total": len(self._substitution_plans),
                "patterns": self.get_substitution_patterns()
            },
            "opponent_scouting": {
                "total_opponents": len(self._opponent_notes),
                "opponents_with_formations": len([n for n in self._opponent_notes.values() if n.recommended_formation])
            }
        }