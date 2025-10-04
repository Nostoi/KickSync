"""
Unit tests for Formation model functionality.

Tests the Formation data structures including FieldPosition, Formation,
SubstitutionPlan, and OpponentNotes with serialization and validation.
"""
import unittest
from unittest.mock import patch
from datetime import date, datetime

from src.models.formation import (
    FieldPosition,
    Formation,
    FormationType,
    Position,
    SubstitutionPlan,
    OpponentNotes,
    FormationTemplates
)


class TestFieldPosition(unittest.TestCase):
    """Test FieldPosition model."""

    def test_field_position_creation(self) -> None:
        """Test creating a field position."""
        position = FieldPosition(
            x=50.0,
            y=25.0,
            position_code="MIDFIELDER",
            player_name="John Doe",
            player_number=10
        )
        
        self.assertEqual(position.x, 50.0)
        self.assertEqual(position.y, 25.0)
        self.assertEqual(position.position_code, "MIDFIELDER")
        self.assertEqual(position.player_name, "John Doe")
        self.assertEqual(position.player_number, 10)

    def test_field_position_defaults(self) -> None:
        """Test field position with default values."""
        position = FieldPosition(x=10.0, y=90.0)
        
        self.assertEqual(position.x, 10.0)
        self.assertEqual(position.y, 90.0)
        self.assertIsNone(position.position_code)
        self.assertIsNone(position.player_name)
        self.assertIsNone(position.player_number)

    def test_field_position_to_dict(self) -> None:
        """Test field position serialization."""
        position = FieldPosition(
            x=30.5,
            y=70.2,
            position_code="DEFENDER",
            player_name="Jane Smith"
        )
        
        result = position.to_dict()
        expected = {
            "x": 30.5,
            "y": 70.2,
            "position_code": "DEFENDER",
            "player_name": "Jane Smith",
            "player_number": None
        }
        
        self.assertEqual(result, expected)

    def test_field_position_from_dict(self) -> None:
        """Test field position deserialization."""
        data = {
            "x": 45.0,
            "y": 55.0,
            "position_code": "GOALKEEPER",
            "player_name": "Bob Johnson",
            "player_number": 1
        }
        
        position = FieldPosition.from_dict(data)
        
        self.assertEqual(position.x, 45.0)
        self.assertEqual(position.y, 55.0)
        self.assertEqual(position.position_code, "GOALKEEPER")
        self.assertEqual(position.player_name, "Bob Johnson")
        self.assertEqual(position.player_number, 1)


class TestFormation(unittest.TestCase):
    """Test Formation model."""

    def setUp(self) -> None:
        """Set up test data."""
        self.test_positions = [
            FieldPosition(x=50, y=5, position_code="GOALKEEPER"),
            FieldPosition(x=25, y=25, position_code="DEFENDER"),
            FieldPosition(x=75, y=25, position_code="DEFENDER"),
            FieldPosition(x=50, y=50, position_code="MIDFIELDER"),
            FieldPosition(x=50, y=80, position_code="FORWARD")
        ]

    def test_formation_creation(self) -> None:
        """Test creating a formation."""
        formation = Formation(
            name="Test Formation",
            formation_type=FormationType.FORMATION_4_4_2,
            description="A test formation",
            positions=self.test_positions
        )
        
        self.assertEqual(formation.name, "Test Formation")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_4_2)
        self.assertEqual(formation.description, "A test formation")
        self.assertEqual(len(formation.positions), 5)
        self.assertIsInstance(formation.created_at, datetime)

    def test_formation_defaults(self) -> None:
        """Test formation with default values."""
        formation = Formation(name="Basic Formation")
        
        self.assertEqual(formation.name, "Basic Formation")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_4_2)
        self.assertEqual(formation.description, "")
        self.assertEqual(formation.positions, [])
        self.assertIsInstance(formation.created_at, datetime)

    def test_formation_to_dict(self) -> None:
        """Test formation serialization."""
        formation = Formation(
            name="Serialization Test",
            formation_type=FormationType.FORMATION_4_3_3,
            description="Testing serialization",
            positions=self.test_positions[:2]  # First 2 positions
        )
        
        result = formation.to_dict()
        
        self.assertEqual(result["name"], "Serialization Test")
        self.assertEqual(result["formation_type"], "4-3-3")
        self.assertEqual(result["description"], "Testing serialization")
        self.assertEqual(len(result["positions"]), 2)
        self.assertIn("created_at", result)
        
        # Check position serialization
        self.assertEqual(result["positions"][0]["position_code"], "GOALKEEPER")
        self.assertEqual(result["positions"][1]["position_code"], "DEFENDER")

    def test_formation_from_dict(self) -> None:
        """Test formation deserialization."""
        data = {
            "name": "Deserialization Test",
            "formation_type": "3-5-2",
            "description": "Testing deserialization",
            "created_at": "2024-01-15T10:30:00",
            "positions": [
                {"x": 50, "y": 5, "position_code": "GOALKEEPER", "player_name": None, "player_number": None},
                {"x": 30, "y": 30, "position_code": "DEFENDER", "player_name": "Test Player", "player_number": 5}
            ]
        }
        
        formation = Formation.from_dict(data)
        
        self.assertEqual(formation.name, "Deserialization Test")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_3_5_2)
        self.assertEqual(formation.description, "Testing deserialization")
        self.assertEqual(len(formation.positions), 2)
        
        # Check positions
        self.assertEqual(formation.positions[0].position_code, "GOALKEEPER")
        self.assertEqual(formation.positions[1].player_name, "Test Player")

    def test_assign_player(self) -> None:
        """Test assigning a player to a position."""
        formation = Formation(name="Assignment Test", positions=self.test_positions.copy())
        
        formation.assign_player(1, "John Doe", 10)  # Assign to second position (index 1)
        
        self.assertEqual(formation.positions[1].player_name, "John Doe")
        self.assertEqual(formation.positions[1].player_number, 10)

    def test_assign_player_invalid_position(self) -> None:
        """Test assigning to invalid position index."""
        formation = Formation(name="Invalid Test", positions=self.test_positions.copy())
        
        # Should not raise exception, just ignore invalid position
        formation.assign_player(10, "John Doe", 10)  # Invalid index
        
        # Original positions should be unchanged
        self.assertIsNone(formation.positions[0].player_name)

    def test_clear_assignments(self) -> None:
        """Test clearing all player assignments."""
        formation = Formation(name="Clear Test", positions=self.test_positions.copy())
        
        # Assign some players
        formation.assign_player(0, "Player 1", 1)
        formation.assign_player(1, "Player 2", 2)
        
        formation.clear_assignments()
        
        # All assignments should be cleared
        for position in formation.positions:
            self.assertIsNone(position.player_name)
            self.assertIsNone(position.player_number)

    def test_get_assigned_players(self) -> None:
        """Test getting list of assigned players."""
        formation = Formation(name="Assigned Test", positions=self.test_positions.copy())
        
        formation.assign_player(0, "Player 1", 1)
        formation.assign_player(2, "Player 3", 3)
        
        assigned = formation.get_assigned_players()
        
        self.assertEqual(len(assigned), 2)
        self.assertIn("Player 1", assigned)
        self.assertIn("Player 3", assigned)

    def test_is_complete(self) -> None:
        """Test checking if formation is complete (11 players)."""
        # Create formation with 11 positions
        positions = []
        for i in range(11):
            positions.append(FieldPosition(x=i*10, y=50, position_code="PLAYER"))
        
        formation = Formation(name="Complete Test", positions=positions)
        
        # Not complete initially
        self.assertFalse(formation.is_complete())
        
        # Assign 11 players
        for i in range(11):
            formation.assign_player(i, f"Player {i+1}", i+1)
        
        # Should be complete now
        self.assertTrue(formation.is_complete())


class TestSubstitutionPlan(unittest.TestCase):
    """Test SubstitutionPlan model."""

    def test_substitution_plan_creation(self) -> None:
        """Test creating a substitution plan."""
        plan = SubstitutionPlan(
            minute=30,
            player_out="John Doe",
            player_in="Jane Smith",
            reason="Tactical change",
            position_change=True
        )
        
        self.assertEqual(plan.minute, 30)
        self.assertEqual(plan.player_out, "John Doe")
        self.assertEqual(plan.player_in, "Jane Smith")
        self.assertEqual(plan.reason, "Tactical change")
        self.assertTrue(plan.position_change)

    def test_substitution_plan_defaults(self) -> None:
        """Test substitution plan with defaults."""
        plan = SubstitutionPlan(minute=45, player_out="Player A", player_in="Player B")
        
        self.assertEqual(plan.minute, 45)
        self.assertEqual(plan.reason, "")
        self.assertFalse(plan.position_change)

    def test_substitution_plan_serialization(self) -> None:
        """Test substitution plan to/from dict."""
        plan = SubstitutionPlan(
            minute=60,
            player_out="Out Player",
            player_in="In Player",
            reason="Injury",
            position_change=True
        )
        
        data = plan.to_dict()
        restored_plan = SubstitutionPlan.from_dict(data)
        
        self.assertEqual(restored_plan.minute, 60)
        self.assertEqual(restored_plan.player_out, "Out Player")
        self.assertEqual(restored_plan.player_in, "In Player")
        self.assertEqual(restored_plan.reason, "Injury")
        self.assertTrue(restored_plan.position_change)


class TestOpponentNotes(unittest.TestCase):
    """Test OpponentNotes model."""

    def test_opponent_notes_creation(self) -> None:
        """Test creating opponent notes."""
        notes = OpponentNotes(
            opponent_name="Rival Team",
            strengths=["Fast wingers", "Strong defense"],
            weaknesses=["Weak on set pieces"],
            key_players=["Star Player #10", "Goalkeeper #1"],
            tactical_notes="They play 4-3-3 formation",
            game_date=date(2024, 1, 15)
        )
        
        self.assertEqual(notes.opponent_name, "Rival Team")
        self.assertEqual(len(notes.strengths), 2)
        self.assertEqual(len(notes.weaknesses), 1)
        self.assertEqual(len(notes.key_players), 2)
        self.assertEqual(notes.tactical_notes, "They play 4-3-3 formation")
        self.assertEqual(notes.game_date, date(2024, 1, 15))

    def test_opponent_notes_defaults(self) -> None:
        """Test opponent notes with defaults."""
        notes = OpponentNotes(opponent_name="Basic Team")
        
        self.assertEqual(notes.opponent_name, "Basic Team")
        self.assertEqual(notes.strengths, [])
        self.assertEqual(notes.weaknesses, [])
        self.assertEqual(notes.key_players, [])
        self.assertEqual(notes.tactical_notes, "")
        self.assertIsNone(notes.game_date)

    def test_opponent_notes_serialization(self) -> None:
        """Test opponent notes serialization."""
        notes = OpponentNotes(
            opponent_name="Test Opponent",
            strengths=["Speed"],
            weaknesses=["Height"],
            key_players=["Player 1"],
            tactical_notes="4-4-2 formation",
            game_date=date(2024, 2, 20)
        )
        
        data = notes.to_dict()
        restored_notes = OpponentNotes.from_dict(data)
        
        self.assertEqual(restored_notes.opponent_name, "Test Opponent")
        self.assertEqual(restored_notes.strengths, ["Speed"])
        self.assertEqual(restored_notes.weaknesses, ["Height"])
        self.assertEqual(restored_notes.key_players, ["Player 1"])
        self.assertEqual(restored_notes.tactical_notes, "4-4-2 formation")
        self.assertEqual(restored_notes.game_date, date(2024, 2, 20))


class TestFormationTemplates(unittest.TestCase):
    """Test FormationTemplates factory."""

    def test_get_all_templates(self) -> None:
        """Test getting all formation templates."""
        templates = FormationTemplates.get_all_templates()
        
        # Should have at least the basic templates
        self.assertGreaterEqual(len(templates), 3)
        
        # Check that we have expected formations
        formation_types = [t.formation_type for t in templates]
        self.assertIn(FormationType.FORMATION_4_4_2, formation_types)
        self.assertIn(FormationType.FORMATION_4_3_3, formation_types)
        self.assertIn(FormationType.FORMATION_3_5_2, formation_types)

    def test_create_formation_442(self) -> None:
        """Test creating 4-4-2 formation."""
        formation = FormationTemplates.create_formation(FormationType.FORMATION_4_4_2, "Test 4-4-2")
        
        self.assertEqual(formation.name, "Test 4-4-2")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_4_2)
        self.assertEqual(len(formation.positions), 11)  # Should have 11 positions
        
        # Check that we have the right position types
        position_codes = [p.position_code for p in formation.positions if p.position_code]
        self.assertIn("GOALKEEPER", position_codes)
        
        # Should have defenders, midfielders, forwards
        defender_positions = [p for p in formation.positions if p.position_code and "BACK" in p.position_code or "DEFENDER" in p.position_code]
        midfielder_positions = [p for p in formation.positions if p.position_code and "MID" in p.position_code]
        forward_positions = [p for p in formation.positions if p.position_code and ("STRIKER" in p.position_code or "FORWARD" in p.position_code)]
        
        self.assertGreaterEqual(len(defender_positions), 3)  # At least 3 defenders
        self.assertGreaterEqual(len(midfielder_positions), 3)  # At least 3 midfielders
        self.assertGreaterEqual(len(forward_positions), 1)  # At least 1 forward

    def test_create_formation_433(self) -> None:
        """Test creating 4-3-3 formation."""
        formation = FormationTemplates.create_formation(FormationType.FORMATION_4_3_3, "Test 4-3-3")
        
        self.assertEqual(formation.name, "Test 4-3-3")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_3_3)
        self.assertEqual(len(formation.positions), 11)

    def test_create_formation_352(self) -> None:
        """Test creating 3-5-2 formation."""
        formation = FormationTemplates.create_formation(FormationType.FORMATION_3_5_2, "Test 3-5-2")
        
        self.assertEqual(formation.name, "Test 3-5-2")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_3_5_2)
        self.assertEqual(len(formation.positions), 11)

    def test_create_custom_formation(self) -> None:
        """Test creating custom formation with specific positions."""
        custom_positions = [
            FieldPosition(x=50, y=10, position_code="GOALKEEPER"),
            FieldPosition(x=30, y=30, position_code="DEFENDER"),
            FieldPosition(x=70, y=30, position_code="DEFENDER"),
            FieldPosition(x=50, y=70, position_code="FORWARD")
        ]
        
        formation = FormationTemplates.create_custom_formation(
            name="Custom Formation",
            formation_type=FormationType.FORMATION_4_4_2,
            positions=custom_positions,
            description="A custom test formation"
        )
        
        self.assertEqual(formation.name, "Custom Formation")
        self.assertEqual(formation.formation_type, FormationType.FORMATION_4_4_2)
        self.assertEqual(formation.description, "A custom test formation")
        self.assertEqual(len(formation.positions), 4)
        self.assertEqual(formation.positions[0].position_code, "GOALKEEPER")


if __name__ == "__main__":
    unittest.main()