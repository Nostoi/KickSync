"""Analytics helpers for the Soccer Coach Sideline Timekeeper."""

from __future__ import annotations

import csv
import datetime as dt
import io
import statistics
from collections import Counter
from typing import List, Optional

from ..models import GameReport, GameState, Player, PlayerTimeSummary
from ..utils import now_ts
from .timer_service import TimerService

FAIRNESS_THRESHOLD_SECONDS = 120  # +/- 2 minutes regarded as notable variance
FAIRNESS_ORDER = {"under": 0, "ok": 1, "over": 2}


class AnalyticsService:
    """Generate reports describing playing time distribution."""

    def __init__(
        self,
        game_state: GameState,
        timer_service: Optional[TimerService] = None,
    ) -> None:
        self.game_state = game_state
        self._timer_service = timer_service

    def set_timer_service(self, timer_service: TimerService) -> None:
        """Attach a timer service instance used for elapsed time queries."""

        self._timer_service = timer_service

    def _timer(self) -> TimerService:
        if self._timer_service is None:
            self._timer_service = TimerService(self.game_state)
        return self._timer_service

    def generate_game_report(self) -> GameReport:
        """Build a :class:`GameReport` snapshot for the active game."""

        timer = self._timer()
        config = timer.get_timer_configuration()

        regulation_seconds = int(config["game_length_seconds"])
        stoppage_seconds = int(config["total_stoppage_seconds"])
        adjustment_seconds = int(config["total_adjustment_seconds"])
        elapsed_seconds = int(timer.get_game_elapsed_seconds())

        roster: List[Player] = list(self.game_state.roster.values())
        roster_size = len(roster)

        target_total = max(0, regulation_seconds + stoppage_seconds + adjustment_seconds)
        target_per_player = target_total / roster_size if roster_size else 0.0
        target_per_player_int = int(round(target_per_player)) if roster_size else 0

        now = now_ts()
        summaries: List[PlayerTimeSummary] = []

        for player in roster:
            stint_seconds = player.current_stint_seconds(now)
            cumulative = player.total_seconds + stint_seconds
            delta = int(round(cumulative - target_per_player))
            fairness = self._classify_fairness(delta)
            bench_seconds = 0
            if elapsed_seconds > 0:
                bench_seconds = max(0, int(elapsed_seconds - cumulative))

            target_share = (
                cumulative / target_per_player if target_per_player > 0 else 0.0
            )

            summaries.append(
                PlayerTimeSummary(
                    name=player.name,
                    number=player.number,
                    preferred_positions=player.preferred_list(),
                    on_field=player.on_field,
                    position=player.position,
                    total_seconds=player.total_seconds,
                    active_stint_seconds=stint_seconds,
                    cumulative_seconds=cumulative,
                    target_seconds=target_per_player_int,
                    delta_seconds=delta,
                    bench_seconds=bench_seconds,
                    target_share=target_share,
                    fairness=fairness,
                )
            )

        summaries.sort(
            key=lambda item: (
                FAIRNESS_ORDER.get(item.fairness, 1),
                item.delta_seconds,
                item.name,
            )
        )
        totals = [summary.cumulative_seconds for summary in summaries]
        fairness_counter = Counter(summary.fairness for summary in summaries)
        fairness_counts = {
            "under": fairness_counter.get("under", 0),
            "ok": fairness_counter.get("ok", 0),
            "over": fairness_counter.get("over", 0),
        }
        for label, value in fairness_counter.items():
            if label not in fairness_counts:
                fairness_counts[label] = value

        average_seconds = statistics.mean(totals) if totals else 0.0
        median_seconds = statistics.median(totals) if totals else 0.0
        min_seconds = min(totals) if totals else 0
        max_seconds = max(totals) if totals else 0

        return GameReport(
            generated_ts=now,
            roster_size=roster_size,
            regulation_seconds=regulation_seconds,
            stoppage_seconds=stoppage_seconds,
            adjustment_seconds=adjustment_seconds,
            elapsed_seconds=elapsed_seconds,
            target_seconds_total=int(target_total),
            target_seconds_per_player=target_per_player_int,
            players=summaries,
            average_seconds=average_seconds,
            median_seconds=median_seconds,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            fairness_counts=fairness_counts,
        )

    def generate_report_csv(self, report: Optional[GameReport] = None) -> str:
        """Return a CSV document describing the current playing time report.

        Args:
            report: Optional pre-generated :class:`GameReport` snapshot. When
                omitted the method generates a fresh report using the attached
                :class:`TimerService`.

        Returns:
            CSV formatted string containing summary information followed by a
            table of player level metrics.

        Raises:
            ValueError: If there are no players to include in the report.
        """

        report = report or self.generate_game_report()
        if report.roster_size == 0:
            raise ValueError("Cannot export analytics without any players")

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")

        generated_dt = dt.datetime.fromtimestamp(report.generated_ts)
        writer.writerow(["Sideline Timekeeper Report"])
        writer.writerow(["Generated", generated_dt.isoformat(timespec="seconds")])
        writer.writerow(["Roster Size", report.roster_size])
        writer.writerow(["Elapsed Seconds", report.elapsed_seconds])
        writer.writerow(["Regulation Seconds", report.regulation_seconds])
        writer.writerow(["Stoppage Seconds", report.stoppage_seconds])
        writer.writerow(["Adjustment Seconds", report.adjustment_seconds])
        writer.writerow(["Target Seconds Total", report.target_seconds_total])
        writer.writerow(["Target Seconds Per Player", report.target_seconds_per_player])
        writer.writerow(["Average Seconds", round(report.average_seconds, 2)])
        writer.writerow(["Median Seconds", round(report.median_seconds, 2)])
        writer.writerow(["Minimum Seconds", report.min_seconds])
        writer.writerow(["Maximum Seconds", report.max_seconds])

        fairness_counts = report.fairness_counts or {}
        writer.writerow(["Players Under Target", fairness_counts.get("under", 0)])
        writer.writerow(["Players On Target", fairness_counts.get("ok", 0)])
        writer.writerow(["Players Over Target", fairness_counts.get("over", 0)])
        writer.writerow([])

        writer.writerow(
            [
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
        )

        for summary in report.players:
            preferred = ", ".join(summary.preferred_positions)
            share_percent = round(summary.target_share * 100, 2)
            writer.writerow(
                [
                    summary.name,
                    summary.number or "",
                    preferred,
                    "yes" if summary.on_field else "no",
                    summary.position or "",
                    summary.total_seconds,
                    summary.active_stint_seconds,
                    summary.cumulative_seconds,
                    summary.target_seconds,
                    summary.delta_seconds,
                    summary.bench_seconds,
                    share_percent,
                    summary.fairness,
                ]
            )

        csv_text = buffer.getvalue()
        buffer.close()
        return csv_text

    @staticmethod
    def _classify_fairness(delta_seconds: int) -> str:
        if delta_seconds <= -FAIRNESS_THRESHOLD_SECONDS:
            return "under"
        if delta_seconds >= FAIRNESS_THRESHOLD_SECONDS:
            return "over"
        return "ok"

