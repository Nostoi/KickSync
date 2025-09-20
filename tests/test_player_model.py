"""
Unit tests for enhanced Player model and related data classes.

Tests serialization, validation, and functionality of ContactInfo, MedicalInfo,
PlayerStats, and GameAttendance classes.
"""
import unittest
import tempfile
import json
from datetime import datetime, date
from typing import Dict, Any

from src.models.player import (
    Player, ContactInfo, MedicalInfo, PlayerStats, GameAttendance
)


class TestPlayerModel(unittest.TestCase):
    """Test cases for enhanced Player model."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.basic_player = Player(
            name="John Doe",
            number="10"
        )
        
        self.enhanced_player = Player(
            name="Jane Smith",
            number="7",
            contact_info=ContactInfo(
                phone="555-1234",
                email="jane@example.com",
                emergency_contact="Bob Smith",
                emergency_phone="555-5678",
                address="123 Main St"
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
                )
            ]
        )
    
    def test_basic_player_creation(self) -> None:
        """Test creating a basic player with minimal information."""
        player = self.basic_player
        
        self.assertEqual(player.name, "John Doe")
        self.assertEqual(player.number, "10")
        self.assertEqual(player.total_seconds, 0)  # Default value
        self.assertIsNotNone(player.contact_info)  # Default factory
        self.assertIsNotNone(player.medical_info)  # Default factory
        self.assertIsNotNone(player.statistics)  # Default factory
        self.assertEqual(len(player.attendance_history), 0)
    
    def test_enhanced_player_creation(self) -> None:
        """Test creating a player with all enhanced information."""
        player = self.enhanced_player
        
        # Basic info
        self.assertEqual(player.name, "Jane Smith")
        self.assertEqual(player.number, "7")
        
        # Contact info
        self.assertIsNotNone(player.contact_info)
        self.assertEqual(player.contact_info.phone, "555-1234")
        self.assertEqual(player.contact_info.email, "jane@example.com")
        
        # Medical info
        self.assertIsNotNone(player.medical_info)
        self.assertIn("peanuts", player.medical_info.allergies)
        self.assertIn("inhaler", player.medical_info.medications)
        
        # Statistics
        self.assertIsNotNone(player.statistics)
        self.assertEqual(player.statistics.goals, 5)
        self.assertEqual(player.statistics.assists, 3)
        
        # Attendance
        self.assertEqual(len(player.attendance_history), 1)
        self.assertTrue(player.attendance_history[0].present)
    
    def test_player_age_calculation(self) -> None:
        """Test age calculation from birth date."""
        # Player with birth date
        player_with_age = Player(
            name="Young Player",
            number="1",
            position="goalkeeper",
            date_of_birth=date(2010, 5, 15)
        )
        
        age = player_with_age.age()
        self.assertIsInstance(age, int)
        self.assertTrue(age > 0)
        
        # Player without birth date
        age_none = self.basic_player.age()
        self.assertIsNone(age_none)
    
    def test_player_to_dict_basic(self) -> None:
        """Test serialization of basic player to dictionary."""
        player_dict = self.basic_player.to_dict()
        
        self.assertEqual(player_dict["name"], "John Doe")
        self.assertEqual(player_dict["number"], "10")
        self.assertEqual(player_dict["position"], None)
        self.assertEqual(player_dict["skill_level"], 5)
        self.assertIsNone(player_dict["contact_info"])
        self.assertIsNone(player_dict["medical_info"])
        self.assertIsNone(player_dict["stats"])
        self.assertEqual(player_dict["attendance"], [])
    
    def test_player_to_dict_enhanced(self) -> None:
        """Test converting player to dictionary with enhanced data."""
        player = Player(
            name="Jane Smith",
            number="7",
            position="forward",
            skill_ratings={"speed": 8, "technique": 7}
        )
        data = player.to_dict()
        self.assertEqual(data["name"], "Jane Smith")
        self.assertEqual(data["number"], "7")
        self.assertEqual(data["position"], "forward")
        self.assertEqual(data["skill_ratings"], {"speed": 8, "technique": 7})
    
    def test_player_from_dict_basic(self) -> None:
        """Test creating player from dictionary with basic data."""
        data = {
            "name": "John Doe",
            "number": "10",
            "position": "midfielder"
        }
        player = Player.from_dict(data)
        self.assertEqual(player.name, "John Doe")
        self.assertEqual(player.number, "10")
        self.assertEqual(player.position, "midfielder")
    
    def test_player_from_dict_enhanced(self) -> None:
        """Test creating player from dictionary with enhanced data."""
        data = {
            "name": "Jane Smith",
            "number": "7",
            "position": "forward",
            "skill_ratings": {"speed": 8, "technique": 7}
        }
        player = Player.from_dict(data)
        self.assertEqual(player.name, "Jane Smith")
        self.assertEqual(player.number, "7")
        self.assertEqual(player.position, "forward")
        self.assertEqual(player.skill_ratings, {"speed": 8, "technique": 7})
    
    def test_player_string_representation(self) -> None:
        """Test player string representation."""
        player = Player(
            name="John Doe",
            number="10",
            position="midfielder"
        )
        self.assertIn("John Doe", str(player))


class TestContactInfo(unittest.TestCase):
    """Test cases for ContactInfo data class."""
    
    def test_contact_info_creation(self) -> None:
        """Test creating contact info with various fields."""
        contact = ContactInfo(
            phone="555-1234",
            email="test@example.com",
            emergency_contact="Emergency Contact",
            emergency_phone="555-9999",
            address="123 Test St"
        )
        
        self.assertEqual(contact.phone, "555-1234")
        self.assertEqual(contact.email, "test@example.com")
        self.assertEqual(contact.emergency_contact, "Emergency Contact")
        self.assertEqual(contact.emergency_phone, "555-9999")
        self.assertEqual(contact.address, "123 Test St")
    
    def test_contact_info_to_dict(self) -> None:
        """Test ContactInfo serialization."""
        contact = ContactInfo(phone="555-1234", email="test@example.com")
        contact_dict = contact.to_dict()
        
        self.assertEqual(contact_dict["phone"], "555-1234")
        self.assertEqual(contact_dict["email"], "test@example.com")
        self.assertIsNone(contact_dict["address"])
    
    def test_contact_info_from_dict(self) -> None:
        """Test ContactInfo deserialization."""
        contact_dict = {
            "phone": "555-5678",
            "email": "from_dict@example.com",
            "address": "Test Address"
        }
        
        contact = ContactInfo.from_dict(contact_dict)
        
        self.assertEqual(contact.phone, "555-5678")
        self.assertEqual(contact.email, "from_dict@example.com")
        self.assertEqual(contact.address, "Test Address")
        self.assertIsNone(contact.emergency_contact)


class TestMedicalInfo(unittest.TestCase):
    """Test cases for MedicalInfo data class."""
    
    def test_medical_info_creation(self) -> None:
        """Test creating medical info."""
        medical = MedicalInfo(
            allergies=["peanuts", "shellfish"],
            medications=["inhaler", "epipen"],
            notes="Severe asthma and food allergies"
        )
        
        self.assertEqual(medical.allergies, ["peanuts", "shellfish"])
        self.assertEqual(medical.medications, ["inhaler", "epipen"])
        self.assertEqual(medical.notes, "Severe asthma and food allergies")
    
    def test_medical_info_empty_lists(self) -> None:
        """Test medical info with empty lists."""
        medical = MedicalInfo()
        
        self.assertEqual(medical.allergies, [])
        self.assertEqual(medical.medications, [])
        self.assertIsNone(medical.notes)
    
    def test_medical_info_serialization(self) -> None:
        """Test MedicalInfo to_dict and from_dict."""
        medical = MedicalInfo(
            allergies=["latex"],
            medications=["aspirin"],
            notes="Take with food"
        )
        
        medical_dict = medical.to_dict()
        restored_medical = MedicalInfo.from_dict(medical_dict)
        
        self.assertEqual(restored_medical.allergies, ["latex"])
        self.assertEqual(restored_medical.medications, ["aspirin"])
        self.assertEqual(restored_medical.notes, "Take with food")


class TestPlayerStats(unittest.TestCase):
    """Test cases for PlayerStats data class."""
    
    def test_player_stats_creation(self) -> None:
        """Test creating player statistics."""
        stats = PlayerStats(
            goals=10,
            assists=5,
            yellow_cards=2,
            red_cards=1,
            games_played=20,
            total_minutes=1800
        )
        
        self.assertEqual(stats.goals, 10)
        self.assertEqual(stats.assists, 5)
        self.assertEqual(stats.yellow_cards, 2)
        self.assertEqual(stats.red_cards, 1)
        self.assertEqual(stats.games_played, 20)
        self.assertEqual(stats.total_minutes, 1800)
    
    def test_player_stats_defaults(self) -> None:
        """Test default values for player statistics."""
        stats = PlayerStats()
        
        self.assertEqual(stats.goals, 0)
        self.assertEqual(stats.assists, 0)
        self.assertEqual(stats.yellow_cards, 0)
        self.assertEqual(stats.red_cards, 0)
        self.assertEqual(stats.games_played, 0)
        self.assertEqual(stats.total_minutes, 0)
    
    def test_player_stats_serialization(self) -> None:
        """Test PlayerStats serialization and deserialization."""
        stats = PlayerStats(goals=7, assists=3, games_played=12, total_minutes=600)
        
        stats_dict = stats.to_dict()
        restored_stats = PlayerStats.from_dict(stats_dict)
        
        self.assertEqual(restored_stats.goals, 7)
        self.assertEqual(restored_stats.assists, 3)
        self.assertEqual(restored_stats.games_played, 12)
        self.assertEqual(restored_stats.total_minutes, 600)


class TestGameAttendance(unittest.TestCase):
    """Test cases for GameAttendance data class."""
    
    def test_game_attendance_creation(self) -> None:
        """Test creating game attendance record."""
        attendance = GameAttendance(
            date=date(2025, 1, 15),
            present=True,
            reason="Full game, excellent performance"
        )
        
        self.assertEqual(attendance.date, date(2025, 1, 15))
        self.assertTrue(attendance.present)
        self.assertEqual(attendance.reason, "Full game, excellent performance")
    
    def test_game_attendance_absent(self) -> None:
        """Test creating attendance record for absent player."""
        attendance = GameAttendance(
            date=date(2025, 1, 20),
            present=False,
            reason="Sick with flu"
        )
        
        self.assertEqual(attendance.date, date(2025, 1, 20))
        self.assertFalse(attendance.present)
        self.assertEqual(attendance.reason, "Sick with flu")
    
    def test_game_attendance_defaults(self) -> None:
        """Test default values for game attendance."""
        attendance = GameAttendance(date=date(2025, 1, 1), present=True)
        
        self.assertEqual(attendance.date, date(2025, 1, 1))
        self.assertTrue(attendance.present)
        self.assertIsNone(attendance.reason)
    
    def test_game_attendance_serialization(self) -> None:
        """Test GameAttendance serialization."""
        attendance = GameAttendance(
            date=date(2025, 2, 1),
            present=True,
            reason="First half only"
        )
        
        attendance_dict = attendance.to_dict()
        restored_attendance = GameAttendance.from_dict(attendance_dict)
        
        self.assertEqual(restored_attendance.date, date(2025, 2, 1))
        self.assertTrue(restored_attendance.present)
        self.assertEqual(restored_attendance.reason, "First half only")


if __name__ == '__main__':
    unittest.main()