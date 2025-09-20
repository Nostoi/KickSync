"""Tests for analytics reporting."""

import pytest

from src.models import GameState, Player
from src.services import AnalyticsService, TimerService


def test_generate_game_report_produces_target_and_fairness():
    state = GameState(
        roster={
            "Alice": Player(name="Alice", number="10", preferred="ST", total_seconds=480),
            "Bob": Player(name="Bob", number="2", preferred="DF", total_seconds=120),
        },
        game_length_seconds=600,
        period_count=2,
        period_elapsed=[400, 0],
        period_adjustments=[20, 0],
        period_stoppage=[10, 0],
        current_period_index=0,
        game_start_ts=1,
        paused=True,
    )
    state.ensure_timer_lists()

    timer_service = TimerService(state)
    analytics = AnalyticsService(state, timer_service)

    report = analytics.generate_game_report()

    assert report.roster_size == 2
    assert report.regulation_seconds == 600
    assert report.stoppage_seconds == 10
    assert report.adjustment_seconds == 20
    assert report.elapsed_seconds == 430
    assert report.target_seconds_total == 630
    assert report.target_seconds_per_player == 315

    assert [summary.name for summary in report.players] == ["Bob", "Alice"]

    players = {summary.name: summary for summary in report.players}
    alice = players["Alice"]
    bob = players["Bob"]

    assert alice.fairness == "over"
    assert alice.delta_seconds == 165
    assert pytest.approx(alice.target_share, rel=1e-4) == alice.cumulative_seconds / report.target_seconds_per_player

    assert bob.fairness == "under"
    assert bob.delta_seconds == -195
    assert pytest.approx(bob.target_share, rel=1e-4) == bob.cumulative_seconds / report.target_seconds_per_player
    assert bob.bench_seconds == 310
