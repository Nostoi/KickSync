"""Test analytics CSV export functionality."""

import unittest
import csv
import io
from datetime import datetime

from src.models import GameState, Player
from src.services import AnalyticsService, TimerService


class TestAnalyticsExport(unittest.TestCase):
    """Test CSV export functionality for analytics reports."""

    def setUp(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        
        # Add some test players with proper string format for preferred positions
        self.player1 = Player("Alice", 10)
        self.player1.preferred = "Forward"  # String format, not list
        
        self.player2 = Player("Bob", 7) 
        self.player2.preferred = "Midfielder, Defender"  # Comma-separated string
        
        self.player3 = Player("Charlie", 3)
        self.player3.preferred = "Goalkeeper"
        
        self.game_state.roster = {
            "Alice": self.player1,
            "Bob": self.player2,
            "Charlie": self.player3
        }
        
        # Set up some playing time
        now = 1640995200  # 2022-01-01 00:00:00 UTC
        self.player1.total_seconds = 1800  # 30 minutes
        self.player2.total_seconds = 1200  # 20 minutes
        self.player3.total_seconds = 600   # 10 minutes
        
        self.timer_service = TimerService(self.game_state)
        self.analytics_service = AnalyticsService(self.game_state, self.timer_service)

    def test_csv_export_format(self):
        """Test that CSV export produces valid CSV format."""
        csv_content = self.analytics_service.export_game_report_csv()
        
        # Should be non-empty string
        self.assertIsInstance(csv_content, str)
        self.assertGreater(len(csv_content), 0)
        
        # Should be valid CSV
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        self.assertGreater(len(rows), 0)

    def test_csv_export_content(self):
        """Test that CSV export contains expected content."""
        csv_content = self.analytics_service.export_game_report_csv()
        
        # Check for expected sections
        self.assertIn("Soccer Coach Sideline Timekeeper", csv_content)
        self.assertIn("Game Summary", csv_content)
        self.assertIn("Playing Time Statistics", csv_content)
        self.assertIn("Player Details", csv_content)
        
        # Check for player data
        self.assertIn("Alice", csv_content)
        self.assertIn("Bob", csv_content)
        self.assertIn("Charlie", csv_content)

    def test_csv_export_headers(self):
        """Test that CSV export contains proper column headers."""
        csv_content = self.analytics_service.export_game_report_csv()
        
        # Expected column headers for player details
        expected_headers = [
            "Name", "Number", "Position", "On Field",
            "Total Seconds", "Active Stint", "Cumulative",
            "Target", "Delta", "Bench Time", "Target Share %", "Fairness"
        ]
        
        for header in expected_headers:
            self.assertIn(header, csv_content)

    def test_csv_export_with_game_time(self):
        """Test CSV export with active game timing."""
        # Configure custom game length BEFORE starting the game
        self.timer_service.configure_game(game_length_minutes=90, period_count=2)
        
        # Start the game
        self.timer_service.start_game()
        
        # Add some stoppage time
        self.timer_service.add_stoppage_time(120)  # 2 minutes
        
        csv_content = self.analytics_service.export_game_report_csv()
        
        # Should include timing information
        self.assertIn("Stoppage Time", csv_content)
        self.assertIn("120", csv_content)  # Stoppage time value
        self.assertIn("5400", csv_content)  # 90 minutes = 5400 seconds

    def test_csv_export_statistics(self):
        """Test that CSV export includes statistical calculations."""
        csv_content = self.analytics_service.export_game_report_csv()
        
        # Should include statistics section
        self.assertIn("Average Playing Time", csv_content)
        self.assertIn("Median Playing Time", csv_content)
        self.assertIn("Minimum Playing Time", csv_content)
        self.assertIn("Maximum Playing Time", csv_content)

    def test_csv_export_with_no_players(self):
        """Test CSV export with empty roster."""
        empty_state = GameState()
        empty_analytics = AnalyticsService(empty_state)
        
        csv_content = empty_analytics.export_game_report_csv()
        
        # Should still produce valid CSV
        self.assertIsInstance(csv_content, str)
        self.assertGreater(len(csv_content), 0)
        
        # Should handle zero roster size gracefully
        self.assertIn("Roster Size:", csv_content)
        self.assertIn("0", csv_content)

    def test_csv_export_fairness_classification(self):
        """Test that CSV export includes fairness classifications."""
        csv_content = self.analytics_service.export_game_report_csv()
        
        # Should include fairness categories
        # (Actual values depend on game configuration and playing time)
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Find the player details section
        player_data_started = False
        for row in rows:
            if len(row) > 0 and row[0] == "Name":
                player_data_started = True
                continue
            
            if player_data_started and len(row) >= 12:
                fairness = row[11]  # Fairness column
                self.assertIn(fairness.lower(), ["under", "ok", "over"])

    def test_csv_export_timestamp(self):
        """Test that CSV export includes generation timestamp."""
        csv_content = self.analytics_service.export_game_report_csv()
        
        self.assertIn("Generated:", csv_content)
        
        # Should contain a valid timestamp format
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        generated_row = None
        for row in rows:
            if len(row) >= 2 and row[0] == "Generated:":
                generated_row = row
                break
        
        self.assertIsNotNone(generated_row)
        self.assertEqual(len(generated_row), 2)
        
        # Should be parseable as a timestamp
        timestamp_str = generated_row[1]
        try:
            datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail(f"Invalid timestamp format: {timestamp_str}")


if __name__ == '__main__':
    unittest.main()