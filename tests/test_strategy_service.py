"""
Unit tests for StrategyService functionality.

Tests the strategy service including formation management, AI suggestions,
substitution planning, and opponent scouting features.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import date

from src.services.strategy_service import StrategyService
from src.models.formation import Formation, FormationType, FieldPosition, SubstitutionPlan, OpponentNotes
from src.models.player import Player
from src.models.game_state import GameState


class TestStrategyService(unittest.TestCase):
    """Test StrategyService functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        from src.models.game_state import GameState
        game_state = GameState()
        self.strategy_service = StrategyService(game_state)
        
        # Create test players
        self.test_players = [
            Player(name="Goalkeeper Joe", number=1, position="goalkeeper"),
            Player(name="Defender Dan", number=2, position="defender"),
            Player(name="Defender Dave", number=3, position="defender"), 
            Player(name="Midfielder Mike", number=8, position="midfielder"),
            Player(name="Midfielder Mary", number=10, position="midfielder"),
            Player(name="Forward Frank", number=9, position="forward"),
            Player(name="Forward Fiona", number=11, position="forward"),
        ]
        
        # Create test formation
        self.test_formation = Formation(
            name="Test Formation",
            formation_type=FormationType.FORMATION_4_4_2,
            positions=[
                FieldPosition(x=50, y=5, position_code="GOALKEEPER"),
                FieldPosition(x=25, y=25, position_code="DEFENDER"),
                FieldPosition(x=75, y=25, position_code="DEFENDER"),
                FieldPosition(x=50, y=50, position_code="MIDFIELDER"),
                FieldPosition(x=50, y=80, position_code="FORWARD")
            ]
        )

    def test_create_formation(self) -> None:
        """Test creating a new formation."""
        formation = self.strategy_service.create_formation(
            name="New Formation",
            formation_type=FormationType.FORMATION_4_3_3,
            description="A new test formation"
        )
        
        self.assertEqual(formation.name, "New Formation")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_3_3)
        self.assertEqual(formation.description, "A new test formation")
        self.assertEqual(len(formation.positions), 11)  # Should create 11 positions

    def test_create_formation_duplicate_name(self) -> None:
        """Test creating formation with duplicate name fails."""
        # Add first formation
        formation1 = self.strategy_service.create_formation("Duplicate Name", FormationType.FORMATION_4_4_2)
        
        # Try to add second formation with same name
        with self.assertRaises(StrategyError):
            self.strategy_service.create_formation("Duplicate Name", FormationType.FORMATION_4_3_3)

    def test_get_formation(self) -> None:
        """Test retrieving a formation by name."""
        # Create and store formation
        created = self.strategy_service.create_formation("Retrievable", FormationType.FORMATION_3_5_2)
        
        # Retrieve it
        retrieved = self.strategy_service.get_formation("Retrievable")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Retrievable")
        self.assertEqual(retrieved.formation_type, FormationType.FORMATION_3_5_2)

    def test_get_formation_not_found(self) -> None:
        """Test retrieving non-existent formation returns None."""
        result = self.strategy_service.get_formation("Non-existent Formation")
        self.assertIsNone(result)

    def test_list_formations(self) -> None:
        """Test listing all formations."""
        # Initially empty
        formations = self.strategy_service.list_formations()
        self.assertEqual(len(formations), 0)
        
        # Add some formations
        self.strategy_service.create_formation("Formation 1", FormationType.FORMATION_4_4_2)
        self.strategy_service.create_formation("Formation 2", FormationType.FORMATION_4_3_3)
        
        formations = self.strategy_service.list_formations()
        self.assertEqual(len(formations), 2)
        
        names = [f.name for f in formations]
        self.assertIn("Formation 1", names)
        self.assertIn("Formation 2", names)

    def test_delete_formation(self) -> None:
        """Test deleting a formation."""
        # Create formation
        self.strategy_service.create_formation("To Delete", FormationType.FORMATION_4_4_2)
        
        # Verify it exists
        self.assertIsNotNone(self.strategy_service.get_formation("To Delete"))
        
        # Delete it
        result = self.strategy_service.delete_formation("To Delete")
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertIsNone(self.strategy_service.get_formation("To Delete"))

    def test_delete_formation_not_found(self) -> None:
        """Test deleting non-existent formation returns False."""
        result = self.strategy_service.delete_formation("Non-existent")
        self.assertFalse(result)

    def test_assign_player_to_position(self) -> None:
        """Test assigning a player to a formation position."""
        # Create formation
        formation = self.strategy_service.create_formation("Assignment Test", FormationType.FORMATION_4_4_2)
        
        # Assign player
        updated = self.strategy_service.assign_player_to_position("Assignment Test", 0, "Test Player", 99)
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.positions[0].player_name, "Test Player")
        self.assertEqual(updated.positions[0].player_number, 99)

    def test_assign_player_invalid_formation(self) -> None:
        """Test assigning to non-existent formation raises error."""
        with self.assertRaises(StrategyError):
            self.strategy_service.assign_player_to_position("Non-existent", 0, "Player", 1)

    def test_assign_player_invalid_position(self) -> None:
        """Test assigning to invalid position index raises error."""
        formation = self.strategy_service.create_formation("Invalid Position Test", FormationType.FORMATION_4_4_2)
        
        with self.assertRaises(StrategyError):
            self.strategy_service.assign_player_to_position("Invalid Position Test", 99, "Player", 1)

    def test_assign_multiple_players(self) -> None:
        """Test assigning multiple players at once."""
        formation = self.strategy_service.create_formation("Multiple Assignment", FormationType.FORMATION_4_4_2)
        
        assignments = {
            0: ("Player 1", 1),
            1: ("Player 2", 2),
            2: ("Player 3", 3)
        }
        
        updated = self.strategy_service.assign_multiple_players("Multiple Assignment", assignments)
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.positions[0].player_name, "Player 1")
        self.assertEqual(updated.positions[1].player_name, "Player 2")
        self.assertEqual(updated.positions[2].player_name, "Player 3")

    def test_clear_formation_assignments(self) -> None:
        """Test clearing all assignments from a formation."""
        # Create formation and assign players
        formation = self.strategy_service.create_formation("Clear Test", FormationType.FORMATION_4_4_2)
        self.strategy_service.assign_player_to_position("Clear Test", 0, "Player 1", 1)
        self.strategy_service.assign_player_to_position("Clear Test", 1, "Player 2", 2)
        
        # Clear assignments
        updated = self.strategy_service.clear_formation_assignments("Clear Test")
        
        self.assertIsNotNone(updated)
        for position in updated.positions:
            self.assertIsNone(position.player_name)
            self.assertIsNone(position.player_number)

    def test_suggest_optimal_formation_balanced_team(self) -> None:
        """Test formation suggestion for balanced team."""
        suggestion = self.strategy_service.suggest_optimal_formation(self.test_players)
        
        self.assertIsNotNone(suggestion)
        self.assertIn("suggestion", suggestion)
        self.assertIn("formation", suggestion)
        self.assertIsInstance(suggestion["formation"], Formation)

    def test_suggest_optimal_formation_no_players(self) -> None:
        """Test formation suggestion with no players."""
        suggestion = self.strategy_service.suggest_optimal_formation([])
        
        self.assertIsNotNone(suggestion)
        self.assertIn("suggestion", suggestion)
        # Should still suggest a formation even with no players

    def test_suggest_optimal_formation_many_defenders(self) -> None:
        """Test formation suggestion with many defenders."""
        defensive_players = [
            Player(name="GK", number=1, position="goalkeeper"),
            Player(name="Def1", number=2, position="defender"),
            Player(name="Def2", number=3, position="defender"),
            Player(name="Def3", number=4, position="defender"),
            Player(name="Def4", number=5, position="defender"),
            Player(name="Def5", number=6, position="defender"),
            Player(name="Mid1", number=8, position="midfielder"),
        ]
        
        suggestion = self.strategy_service.suggest_optimal_formation(defensive_players)
        
        self.assertIsNotNone(suggestion)
        # Should suggest a defensive formation (like 5-4-1 or 5-3-2)
        suggested_formation = suggestion["formation"]
        self.assertIn("5", suggested_formation.formation_type.value or suggested_formation.name)

    def test_create_substitution_plan(self) -> None:
        """Test creating a substitution plan."""
        plan = self.strategy_service.create_substitution_plan(
            minute=45,
            player_out="Tired Player",
            player_in="Fresh Player",
            reason="Tactical change"
        )
        
        self.assertEqual(plan.minute, 45)
        self.assertEqual(plan.player_out, "Tired Player")
        self.assertEqual(plan.player_in, "Fresh Player")
        self.assertEqual(plan.reason, "Tactical change")

    def test_suggest_substitutions_basic(self) -> None:
        """Test basic substitution suggestions."""
        # Create a game state with some players
        game_state = GameState()
        for player in self.test_players[:5]:
            game_state.roster[player.name] = player
        
        suggestions = self.strategy_service.suggest_substitutions(game_state, minute=60)
        
        self.assertIsInstance(suggestions, list)
        # With basic logic, might not have suggestions without more context

    def test_suggest_substitutions_with_formation(self) -> None:
        """Test substitution suggestions with active formation."""
        game_state = GameState()
        for player in self.test_players:
            game_state.roster[player.name] = player
        
        # Set current formation
        formation = self.strategy_service.create_formation("Active Formation", FormationType.FORMATION_4_4_2)
        formation.assign_player(0, "Goalkeeper Joe", 1)
        formation.assign_player(1, "Defender Dan", 2)
        game_state.current_formation = formation
        
        suggestions = self.strategy_service.suggest_substitutions(game_state, minute=75)
        
        self.assertIsInstance(suggestions, list)

    def test_create_opponent_notes(self) -> None:
        """Test creating opponent scouting notes."""
        notes = self.strategy_service.create_opponent_notes(
            opponent_name="Rival FC",
            strengths=["Fast attacks", "Strong defense"],
            weaknesses=["Weak on corners"],
            key_players=["#10 Striker", "#1 Goalkeeper"],
            tactical_notes="They prefer 4-3-3 formation",
            game_date=date(2024, 1, 15)
        )
        
        self.assertEqual(notes.opponent_name, "Rival FC")
        self.assertEqual(len(notes.strengths), 2)
        self.assertEqual(len(notes.weaknesses), 1)
        self.assertEqual(len(notes.key_players), 2)
        self.assertEqual(notes.tactical_notes, "They prefer 4-3-3 formation")
        self.assertEqual(notes.game_date, date(2024, 1, 15))

    def test_store_and_retrieve_opponent_notes(self) -> None:
        """Test storing and retrieving opponent notes."""
        # Store notes
        notes = self.strategy_service.create_opponent_notes(
            opponent_name="Test Opponent",
            strengths=["Speed"],
            game_date=date(2024, 2, 1)
        )
        self.strategy_service.store_opponent_notes(notes)
        
        # Retrieve notes
        retrieved = self.strategy_service.get_opponent_notes("Test Opponent")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.opponent_name, "Test Opponent")
        self.assertEqual(retrieved.strengths, ["Speed"])

    def test_list_opponent_notes(self) -> None:
        """Test listing all opponent notes."""
        # Initially empty
        notes_list = self.strategy_service.list_opponent_notes()
        self.assertEqual(len(notes_list), 0)
        
        # Add some notes
        notes1 = self.strategy_service.create_opponent_notes("Team A")
        notes2 = self.strategy_service.create_opponent_notes("Team B")
        self.strategy_service.store_opponent_notes(notes1)
        self.strategy_service.store_opponent_notes(notes2)
        
        notes_list = self.strategy_service.list_opponent_notes()
        self.assertEqual(len(notes_list), 2)

    def test_formation_templates(self) -> None:
        """Test getting formation templates."""
        templates = self.strategy_service.get_formation_templates()
        
        self.assertGreater(len(templates), 0)
        
        # Check that templates have proper structure
        for template in templates:
            self.assertIsInstance(template, Formation)
            self.assertIsNotNone(template.name)
            self.assertIsInstance(template.formation_type, FormationType)
            self.assertGreater(len(template.positions), 0)

    def test_create_formation_from_template(self) -> None:
        """Test creating formation from template."""
        formation = self.strategy_service.create_formation_from_template(
            template_type=FormationType.FORMATION_4_4_2,
            name="From Template Test"
        )
        
        self.assertEqual(formation.name, "From Template Test")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_4_2)
        self.assertEqual(len(formation.positions), 11)

    def test_auto_assign_players_to_formation(self) -> None:
        """Test auto-assigning players to formation based on positions."""
        formation = self.strategy_service.create_formation("Auto Assign Test", FormationType.FORMATION_4_4_2)
        
        # Auto-assign based on player positions
        updated = self.strategy_service.auto_assign_players_to_formation("Auto Assign Test", self.test_players)
        
        self.assertIsNotNone(updated)
        
        # Should have assigned the goalkeeper to goalkeeper position
        gk_position = next((p for p in updated.positions if p.position_code == "GOALKEEPER"), None)
        if gk_position:
            self.assertEqual(gk_position.player_name, "Goalkeeper Joe")

    def test_validate_formation_complete(self) -> None:
        """Test validating a complete formation."""
        formation = self.strategy_service.create_formation("Validation Test", FormationType.FORMATION_4_4_2)
        
        # Assign all 11 positions
        for i, player in enumerate(self.test_players[:11] if len(self.test_players) >= 11 else self.test_players):
            if i < len(formation.positions):
                formation.assign_player(i, player.name, player.number)
        
        # Fill remaining positions if needed
        for i in range(len(self.test_players), min(11, len(formation.positions))):
            formation.assign_player(i, f"Extra Player {i}", i + 20)
        
        validation = self.strategy_service.validate_formation(formation)
        
        self.assertIn("valid", validation)
        self.assertIn("issues", validation)

    def test_get_formation_statistics(self) -> None:
        """Test getting formation statistics."""
        formation = self.strategy_service.create_formation("Stats Test", FormationType.FORMATION_4_4_2)
        formation.assign_player(0, "Player 1", 1)
        formation.assign_player(1, "Player 2", 2)
        
        stats = self.strategy_service.get_formation_statistics(formation)
        
        self.assertIn("total_positions", stats)
        self.assertIn("assigned_positions", stats)
        self.assertIn("completion_percentage", stats)
        self.assertEqual(stats["total_positions"], 11)
        self.assertEqual(stats["assigned_positions"], 2)


if __name__ == "__main__":
    unittest.main()