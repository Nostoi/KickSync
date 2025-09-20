"""
Unit tests for PlayerService functionality.

Tests validation, statistics tracking, attendance management, and data operations
for the enhanced player management system.
"""
import unittest
import tempfile
import json
from datetime import datetime, date
from typing import List

from src.services.player_service import PlayerService, PlayerValidationError
from src.models.player import Player, ContactInfo, MedicalInfo, PlayerStats, GameAttendance
from src.services.persistence_service import PersistenceService


class TestPlayerService(unittest.TestCase):
    """Test cases for PlayerService functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        # Create temporary file for testing persistence
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        # Initialize PlayerService with no persistence service for testing
        self.player_service = PlayerService()
        
        # Create test players
        self.test_player_basic = Player(
            name="John Doe",
            number="10"
        )
        
        self.test_player_enhanced = Player(
            name="Jane Smith",
            number="7",
            skill_ratings={"speed": 8, "technique": 7},
            contact_info=ContactInfo(
                phone="555-1234",
                email="jane@example.com",
                address="Susan Smith",
                emergency_contact="Bob Smith",
                emergency_phone="555-5678"
            ),
            medical_info=MedicalInfo(
                allergies=["peanuts", "shellfish"],
                medications=["inhaler"],
                notes="Asthma - inhaler required"
            ),
            statistics=PlayerStats(
                goals=5,
                assists=3,
                yellow_cards=1,
                red_cards=0,
                games_played=10,
                total_minutes=450
            ),
            attendance_history=[
                GameAttendance(
                    date=date(2025, 1, 15),
                    present=True,
                    reason="Played full first half"
                ),
                GameAttendance(
                    date=date(2025, 1, 20),
                    present=False,
                    reason="Sick"
                )
            ]
        )
    
    def tearDown(self) -> None:
        """Clean up after each test method."""
        import os
        try:
            os.unlink(self.temp_file.name)
        except FileNotFoundError:
            pass
    
    def test_validate_player_valid_basic(self) -> None:
        """Test validation of basic valid player."""
        # Should not raise any exception
        self.player_service.validate_player(self.test_player_basic)
    
    def test_validate_player_valid_enhanced(self) -> None:
        """Test validation of enhanced valid player."""
        # Should not raise any exception
        self.player_service.validate_player(self.test_player_enhanced)
    
    def test_validate_player_invalid_name(self) -> None:
        """Test validation fails for invalid names."""
        invalid_players = [
            Player(name="", number=1, position="forward"),  # Empty name
            Player(name="   ", number=1, position="forward"),  # Whitespace only
            Player(name="A" * 101, number=1, position="forward"),  # Too long
        ]
        
        for player in invalid_players:
            with self.assertRaises(PlayerValidationError):
                self.player_service.validate_player(player)
    
    def test_validate_player_invalid_number(self) -> None:
        """Test validation fails for invalid numbers."""
        invalid_players = [
            Player(name="John", number=0, position="forward"),  # Too low
            Player(name="John", number=100, position="forward"),  # Too high
        ]
        
        for player in invalid_players:
            with self.assertRaises(PlayerValidationError):
                self.player_service.validate_player(player)
    
    def test_validate_player_invalid_position(self) -> None:
        """Test validation fails for invalid positions."""
        invalid_player = Player(name="John", number=1, position="invalid_position")
        with self.assertRaises(PlayerValidationError):
            self.player_service.validate_player(invalid_player)
    
    def test_validate_player_invalid_skill_level(self) -> None:
        """Test validation fails for invalid skill levels."""
        invalid_players = [
            Player(name="John", number=1, position="forward", skill_level=0),  # Too low
            Player(name="John", number=1, position="forward", skill_level=11),  # Too high
        ]
        
        for player in invalid_players:
            with self.assertRaises(PlayerValidationError):
                self.player_service.validate_player(player)
    
    def test_validate_player_invalid_contact_info(self) -> None:
        """Test validation fails for invalid contact info."""
        invalid_contact = ContactInfo(
            email="invalid-email"  # Invalid email format
        )
        invalid_player = Player(
            name="John", 
            number=1, 
            position="forward",
            contact_info=invalid_contact
        )
        with self.assertRaises(PlayerValidationError):
            self.player_service.validate_player(invalid_player)
    
    def test_add_player_success(self) -> None:
        """Test successfully adding a player."""
        players = [self.test_player_basic]
        self.player_service.add_player(players, self.test_player_enhanced)
        
        self.assertEqual(len(players), 2)
        self.assertIn(self.test_player_enhanced, players)
    
    def test_add_player_duplicate_name(self) -> None:
        """Test adding player with duplicate name fails."""
        players = [self.test_player_basic]
        duplicate_player = Player(name="John Doe", number=20, position="defender")
        
        with self.assertRaises(PlayerValidationError):
            self.player_service.add_player(players, duplicate_player)
    
    def test_add_player_duplicate_number(self) -> None:
        """Test adding player with duplicate number fails."""
        players = [self.test_player_basic]
        duplicate_player = Player(name="Different Name", number=10, position="defender")
        
        with self.assertRaises(PlayerValidationError):
            self.player_service.add_player(players, duplicate_player)
    
    def test_update_player_success(self) -> None:
        """Test successfully updating a player."""
        players = [self.test_player_basic.copy()]
        
        updated_player = Player(
            name="John Doe",
            number=10,
            position="defender",  # Changed position
            skill_level=7  # Added skill level
        )
        
        result = self.player_service.update_player(players, "John Doe", updated_player)
        
        self.assertTrue(result)
        self.assertEqual(players[0].position, "defender")
        self.assertEqual(players[0].skill_level, 7)
    
    def test_update_player_not_found(self) -> None:
        """Test updating non-existent player fails."""
        players = [self.test_player_basic]
        
        result = self.player_service.update_player(players, "Non-existent", self.test_player_enhanced)
        
        self.assertFalse(result)
    
    def test_delete_player_success(self) -> None:
        """Test successfully deleting a player."""
        players = [self.test_player_basic.copy()]
        
        result = self.player_service.delete_player(players, "John Doe")
        
        self.assertTrue(result)
        self.assertEqual(len(players), 0)
    
    def test_delete_player_not_found(self) -> None:
        """Test deleting non-existent player fails."""
        players = [self.test_player_basic]
        
        result = self.player_service.delete_player(players, "Non-existent")
        
        self.assertFalse(result)
        self.assertEqual(len(players), 1)
    
    def test_find_player_by_name_success(self) -> None:
        """Test finding player by name."""
        players = [self.test_player_basic, self.test_player_enhanced]
        
        found_player = self.player_service.find_player_by_name(players, "Jane Smith")
        
        self.assertIsNotNone(found_player)
        self.assertEqual(found_player.name, "Jane Smith")
    
    def test_find_player_by_name_not_found(self) -> None:
        """Test finding non-existent player returns None."""
        players = [self.test_player_basic]
        
        found_player = self.player_service.find_player_by_name(players, "Non-existent")
        
        self.assertIsNone(found_player)
    
    def test_get_players_by_position(self) -> None:
        """Test filtering players by position."""
        midfielder = Player(name="Mid Player", number=8, position="midfielder")
        forward = Player(name="Forward Player", number=9, position="forward")
        players = [midfielder, forward, self.test_player_enhanced]  # forward
        
        forwards = self.player_service.get_players_by_position(players, "forward")
        midfielders = self.player_service.get_players_by_position(players, "midfielder")
        
        self.assertEqual(len(forwards), 2)
        self.assertEqual(len(midfielders), 1)
        self.assertEqual(midfielders[0].name, "Mid Player")
    
    def test_get_position_recommendations(self) -> None:
        """Test position recommendations based on skill level."""
        recommendations = self.player_service.get_position_recommendations(9)
        
        self.assertIn("forward", recommendations)
        self.assertIn("midfielder", recommendations)
        
        # Low skill level should recommend all positions
        low_skill_recs = self.player_service.get_position_recommendations(3)
        self.assertEqual(len(low_skill_recs), 4)  # All positions
    
    def test_update_player_stats(self) -> None:
        """Test updating player statistics."""
        player = self.test_player_enhanced.copy()
        original_goals = player.stats.goals
        
        self.player_service.update_player_stats(
            player, 
            goals=2, 
            assists=1, 
            minutes_played=90
        )
        
        self.assertEqual(player.stats.goals, original_goals + 2)
        self.assertEqual(player.stats.assists, 4)  # 3 + 1
        self.assertEqual(player.stats.total_minutes, 540)  # 450 + 90
        self.assertEqual(player.stats.games_played, 11)  # 10 + 1
    
    def test_update_player_stats_no_existing_stats(self) -> None:
        """Test updating stats for player with no existing stats."""
        player = self.test_player_basic.copy()
        
        self.player_service.update_player_stats(
            player,
            goals=1,
            assists=2,
            minutes_played=45
        )
        
        self.assertIsNotNone(player.stats)
        self.assertEqual(player.stats.goals, 1)
        self.assertEqual(player.stats.assists, 2)
        self.assertEqual(player.stats.total_minutes, 45)
        self.assertEqual(player.stats.games_played, 1)
    
    def test_add_attendance_record(self) -> None:
        """Test adding attendance record."""
        player = self.test_player_basic.copy()
        
        self.player_service.add_attendance_record(
            player,
            game_date="2025-02-01",
            present=True,
            minutes_played=60,
            notes="Good performance"
        )
        
        self.assertEqual(len(player.attendance), 1)
        self.assertEqual(player.attendance[0].date, "2025-02-01")
        self.assertTrue(player.attendance[0].present)
        self.assertEqual(player.attendance[0].minutes_played, 60)
        self.assertEqual(player.attendance[0].notes, "Good performance")
    
    def test_add_attendance_record_existing_records(self) -> None:
        """Test adding attendance record to player with existing records."""
        player = self.test_player_enhanced.copy()
        original_count = len(player.attendance)
        
        self.player_service.add_attendance_record(
            player,
            game_date="2025-02-01",
            present=True,
            minutes_played=90
        )
        
        self.assertEqual(len(player.attendance), original_count + 1)
        self.assertEqual(player.attendance[-1].date, "2025-02-01")
    
    def test_get_attendance_summary(self) -> None:
        """Test getting attendance summary."""
        player = self.test_player_enhanced.copy()
        
        summary = self.player_service.get_attendance_summary(player)
        
        self.assertEqual(summary["total_games"], 2)
        self.assertEqual(summary["games_attended"], 1)
        self.assertEqual(summary["games_missed"], 1)
        self.assertEqual(summary["attendance_rate"], 50.0)
        self.assertEqual(summary["total_minutes_played"], 45)
    
    def test_get_attendance_summary_no_records(self) -> None:
        """Test getting attendance summary for player with no records."""
        player = self.test_player_basic.copy()
        
        summary = self.player_service.get_attendance_summary(player)
        
        self.assertEqual(summary["total_games"], 0)
        self.assertEqual(summary["games_attended"], 0)
        self.assertEqual(summary["games_missed"], 0)
        self.assertEqual(summary["attendance_rate"], 0.0)
        self.assertEqual(summary["total_minutes_played"], 0)
    
    def test_import_players_from_csv_basic(self) -> None:
        """Test importing basic players from CSV data."""
        csv_data = """name,number,position
John Doe,10,midfielder
Jane Smith,7,forward
Bob Johnson,3,defender"""
        
        existing_players = []
        result = self.player_service.import_players_from_csv(existing_players, csv_data)
        
        self.assertEqual(result["added"], 3)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(existing_players), 3)
        
        # Check first player
        john = next(p for p in existing_players if p.name == "John Doe")
        self.assertEqual(john.number, 10)
        self.assertEqual(john.position, "midfielder")
    
    def test_import_players_from_csv_with_skill_level(self) -> None:
        """Test importing players with skill levels from CSV."""
        csv_data = """name,number,position,skill_level
Advanced Player,1,goalkeeper,9
Beginner Player,99,defender,3"""
        
        existing_players = []
        result = self.player_service.import_players_from_csv(existing_players, csv_data)
        
        self.assertEqual(result["added"], 2)
        advanced = next(p for p in existing_players if p.name == "Advanced Player")
        self.assertEqual(advanced.skill_level, 9)
    
    def test_import_players_update_existing(self) -> None:
        """Test importing players updates existing players."""
        existing_players = [self.test_player_basic.copy()]
        
        csv_data = """name,number,position,skill_level
John Doe,10,defender,8
New Player,5,midfielder,6"""
        
        result = self.player_service.import_players_from_csv(existing_players, csv_data)
        
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(existing_players), 2)
        
        # Check updated player
        john = next(p for p in existing_players if p.name == "John Doe")
        self.assertEqual(john.position, "defender")  # Updated from midfielder
        self.assertEqual(john.skill_level, 8)  # Added skill level
    
    def test_export_players_to_csv_basic(self) -> None:
        """Test exporting basic players to CSV."""
        players = [self.test_player_basic, self.test_player_enhanced]
        
        csv_output = self.player_service.export_players_to_csv(players)
        
        self.assertIn("name,number,position,skill_level", csv_output)
        self.assertIn("John Doe,10,midfielder,5", csv_output)
        self.assertIn("Jane Smith,7,forward,8", csv_output)
    
    def test_export_players_to_csv_empty_list(self) -> None:
        """Test exporting empty player list."""
        csv_output = self.player_service.export_players_to_csv([])
        
        # Should still have header
        self.assertEqual(csv_output.strip(), "name,number,position,skill_level")
    
    def test_get_team_statistics(self) -> None:
        """Test getting team-wide statistics."""
        players = [self.test_player_basic, self.test_player_enhanced]
        
        stats = self.player_service.get_team_statistics(players)
        
        self.assertEqual(stats["total_players"], 2)
        self.assertEqual(stats["total_goals"], 5)  # Only enhanced player has stats
        self.assertEqual(stats["total_assists"], 3)
        self.assertEqual(stats["players_with_stats"], 1)
        self.assertIn("midfielder", stats["position_distribution"])
        self.assertIn("forward", stats["position_distribution"])
        self.assertEqual(stats["position_distribution"]["midfielder"], 1)
        self.assertEqual(stats["position_distribution"]["forward"], 1)
    
    def test_get_team_statistics_empty_list(self) -> None:
        """Test getting statistics for empty team."""
        stats = self.player_service.get_team_statistics([])
        
        self.assertEqual(stats["total_players"], 0)
        self.assertEqual(stats["total_goals"], 0)
        self.assertEqual(stats["total_assists"], 0)
        self.assertEqual(stats["players_with_stats"], 0)
        self.assertEqual(stats["position_distribution"], {})


if __name__ == '__main__':
    unittest.main()