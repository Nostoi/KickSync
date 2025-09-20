import unittest
from unittest.mock import patch

from src.models import GameState
from src.services import TimerService


class TimerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = GameState()
        self.service = TimerService(self.state)

    def test_configure_game_resets_periods(self) -> None:
        self.service.configure_game(game_length_minutes=70, period_count=2)
        self.assertEqual(self.state.game_length_seconds, 70 * 60)
        self.assertEqual(self.state.period_count, 2)
        self.assertEqual(self.state.period_elapsed, [0, 0])
        self.assertEqual(self.state.period_adjustments, [0, 0])
        self.assertEqual(self.state.period_stoppage, [0, 0])

        with patch("src.services.timer_service.now_ts", return_value=1000):
            self.service.start_game()

        with self.assertRaises(ValueError):
            self.service.configure_game(game_length_minutes=60)

    def test_adjustments_and_stoppage_tracking(self) -> None:
        self.service.configure_game(game_length_minutes=60, period_count=2)

        self.service.add_time_adjustment(15)
        self.assertEqual(self.state.period_adjustments, [15, 0])
        self.assertEqual(self.state.elapsed_adjustment, 15)

        self.service.add_time_adjustment(-5, period_index=1)
        self.assertEqual(self.state.period_adjustments, [15, -5])
        self.assertEqual(self.state.elapsed_adjustment, 10)

        self.service.add_time_adjustment(10, apply_to_all=True)
        self.assertEqual(self.state.period_adjustments, [25, 5])
        self.assertEqual(self.state.elapsed_adjustment, 30)

        self.service.add_stoppage_time(30)
        self.assertEqual(self.state.period_stoppage[0], 30)
        self.service.add_stoppage_time(-100, period_index=0)
        self.assertEqual(self.state.period_stoppage[0], 0)

    def test_elapsed_and_remaining_seconds(self) -> None:
        self.service.configure_game(game_length_minutes=60, period_count=2)

        with patch("src.services.timer_service.now_ts", return_value=1000):
            self.service.start_game()

        with patch("src.services.timer_service.now_ts", return_value=1600):
            self.service.pause_game()

        # 10 minutes regulation in first period
        self.assertEqual(self.state.period_elapsed[0], 600)

        self.service.add_time_adjustment(30)
        self.service.add_stoppage_time(60)

        self.assertEqual(self.service.get_game_elapsed_seconds(), 600 + 30 + 60)
        expected_remaining = (60 * 60 + 60) - (600 + 30 + 60)
        self.assertEqual(self.service.get_remaining_seconds(), expected_remaining)
        self.assertFalse(self.service.should_suggest_halftime())

        # Force suggestion by setting elapsed to target
        config = self.service.get_timer_configuration()
        target_first = config["period_lengths"][0] + self.state.period_adjustments[0] + self.state.period_stoppage[0]
        self.state.period_elapsed[0] = target_first
        self.assertTrue(self.service.should_suggest_halftime())

        with patch("src.services.timer_service.now_ts", return_value=2000):
            self.service.start_halftime()

        self.assertTrue(self.state.halftime_started)
        self.assertTrue(self.state.paused)

        with patch("src.services.timer_service.now_ts", return_value=2100):
            self.service.end_halftime()

        self.assertEqual(self.state.current_period_index, 1)
        self.assertFalse(self.state.paused)
        self.assertFalse(self.state.halftime_started)
        self.assertIsNotNone(self.state.period_start_ts)

        with patch("src.services.timer_service.now_ts", return_value=2200):
            summaries = self.service.get_period_summaries()

        self.assertEqual(len(summaries), 2)
        self.assertGreaterEqual(summaries[0]["elapsed_seconds"], self.state.period_elapsed[0])
        refreshed_config = self.service.get_timer_configuration()
        self.assertEqual(refreshed_config["period_count"], 2)
        self.assertEqual(refreshed_config["total_stoppage_seconds"], sum(self.state.period_stoppage))


if __name__ == "__main__":
    unittest.main()
