"""Tests for analytics reporting."""

import csv
import io

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

    assert report.fairness_counts == {"under": 1, "ok": 0, "over": 1}


def test_generate_report_csv_contains_player_rows():
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

    analytics = AnalyticsService(state, TimerService(state))
    report = analytics.generate_game_report()
    csv_text = analytics.generate_report_csv(report)

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    assert rows[0] == ["Sideline Timekeeper Report"]
    assert ["Players Under Target", "1"] in rows
    assert ["Players On Target", "0"] in rows
    assert ["Players Over Target", "1"] in rows
    assert report.fairness_counts == {"under": 1, "ok": 0, "over": 1}

    header = [
        "Name",
        "Number",
        "Preferred Positions",
        "On Field",
        "Position",
        "Total Seconds",
        "Active Stint Seconds",
        "Cumulative Seconds",
        "Target Seconds",
        "Delta Seconds",
        "Bench Seconds",
        "Target Share (%)",
        "Fairness",
    ]
    assert header in rows
    header_index = rows.index(header)
    player_rows = rows[header_index + 1 : header_index + 1 + report.roster_size]
    assert len(player_rows) == report.roster_size

    data = {row[0]: row for row in player_rows}
    assert "Alice" in data and "Bob" in data

    alice_row = data["Alice"]
    bob_row = data["Bob"]

    assert alice_row[1] == "10"
    assert bob_row[1] == "2"
    assert alice_row[-1] == "over"
    assert bob_row[-1] == "under"

    assert float(alice_row[10]) == report.players[1].bench_seconds
    assert pytest.approx(float(bob_row[11]), rel=1e-6) == round(report.players[0].target_share * 100, 2)


def test_generate_report_csv_without_report_argument():
    state = GameState(
        roster={
            "Casey": Player(
                name="Casey",
                number="8",
                preferred="MF",
                total_seconds=390,
            )
        },
        game_length_seconds=600,
        period_count=2,
        period_elapsed=[300, 0],
        period_adjustments=[0, 0],
        period_stoppage=[0, 0],
        current_period_index=0,
        game_start_ts=1,
        paused=True,
    )
    state.ensure_timer_lists()

    analytics = AnalyticsService(state, TimerService(state))
    csv_text = analytics.generate_report_csv()

    rows = list(csv.reader(io.StringIO(csv_text)))

    assert ["Roster Size", "1"] in rows
    assert ["Players Under Target", "1"] in rows
    assert ["Players On Target", "0"] in rows
    assert ["Players Over Target", "0"] in rows
    assert analytics.generate_game_report().fairness_counts == {"under": 1, "ok": 0, "over": 0}


def test_generate_report_csv_requires_players():
    state = GameState()
    analytics = AnalyticsService(state, TimerService(state))
    report = analytics.generate_game_report()
    with pytest.raises(ValueError):
        analytics.generate_report_csv(report)
