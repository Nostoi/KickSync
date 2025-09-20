"""Timer service for the Soccer Coach Sideline Timekeeper application."""

from typing import Dict, List, Optional, Tuple

from ..models import GameState
from ..utils import now_ts, HALFTIME_PAUSE_MIN


class TimerService:
    """Service for managing game timing, periods, and adjustments."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.game_state.ensure_timer_lists()

        # Backfill legacy states that only tracked a game start timestamp
        if (
            self.game_state.game_start_ts is not None
            and sum(self.game_state.period_elapsed) == 0
        ):
            elapsed = max(0, int(now_ts() - self.game_state.game_start_ts))
            index = min(self.game_state.current_period_index, self.game_state.period_count - 1)
            self.game_state.period_elapsed[index] = elapsed
            if not self.game_state.paused and not self.game_state.halftime_started:
                self.game_state.period_start_ts = now_ts()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def configure_game(
        self,
        *,
        game_length_minutes: Optional[int] = None,
        period_count: Optional[int] = None,
    ) -> None:
        """Configure regulation game length and number of periods.

        Raises:
            ValueError: If attempting to reconfigure after the game has started
                        or with invalid values.
        """

        if self.game_state.game_start_ts is not None:
            raise ValueError("Cannot configure timer after the game has started")

        minutes = (
            int(game_length_minutes)
            if game_length_minutes is not None
            else self.game_state.game_length_seconds // 60
        )
        periods = (
            int(period_count)
            if period_count is not None
            else self.game_state.period_count
        )

        minutes = max(1, minutes)
        periods = max(1, periods)

        total_seconds = minutes * 60
        if total_seconds < periods * 60:
            raise ValueError("Game length must allocate at least 60 seconds per period")

        self.game_state.game_length_seconds = total_seconds
        self.game_state.period_count = periods
        self.game_state.period_elapsed = [0] * periods
        self.game_state.period_adjustments = [0] * periods
        self.game_state.period_stoppage = [0] * periods
        self.game_state.current_period_index = 0
        self.game_state.period_start_ts = None
        self.game_state.elapsed_adjustment = 0
        self.game_state.ensure_timer_lists()

    # ------------------------------------------------------------------
    # Core timer controls
    # ------------------------------------------------------------------
    def start_game(self) -> None:
        """Start or resume the game timer."""

        self.game_state.ensure_timer_lists()
        now = now_ts()

        if self.game_state.game_start_ts is None:
            self.game_state.game_start_ts = now
            self.game_state.current_period_index = 0
            self.game_state.period_elapsed = [0] * self.game_state.period_count

        if self.game_state.period_start_ts is None:
            self.game_state.period_start_ts = now

        self.game_state.paused = False

    def pause_game(self) -> None:
        """Pause the game timer and record elapsed time for the active period."""

        if self.game_state.period_start_ts is not None:
            idx = self.game_state.current_period_index
            self.game_state.period_elapsed[idx] += int(now_ts() - self.game_state.period_start_ts)
            self.game_state.period_start_ts = None

        self.game_state.paused = True

    def resume_game(self) -> None:
        """Resume the game after a pause without resetting the period."""

        if self.game_state.game_start_ts is None:
            self.start_game()
            return

        self.game_state.paused = False
        if self.game_state.period_start_ts is None:
            self.game_state.period_start_ts = now_ts()

    def reset_game(self) -> None:
        """Reset all timer state while keeping the roster intact."""

        self.game_state.game_start_ts = None
        self.game_state.scheduled_start_ts = None
        self.game_state.paused = True
        self.game_state.halftime_started = False
        self.game_state.halftime_end_ts = None
        self.game_state.elapsed_adjustment = 0
        self.game_state.period_start_ts = None
        self.game_state.current_period_index = 0
        self.game_state.period_elapsed = [0] * self.game_state.period_count
        self.game_state.period_adjustments = [0] * self.game_state.period_count
        self.game_state.period_stoppage = [0] * self.game_state.period_count

    def start_halftime(self) -> None:
        """Begin an interval break (halftime/quarter break)."""

        if self.game_state.halftime_started:
            return

        if self.game_state.period_start_ts is not None:
            idx = self.game_state.current_period_index
            self.game_state.period_elapsed[idx] += int(now_ts() - self.game_state.period_start_ts)
            self.game_state.period_start_ts = None

        current_time = now_ts()
        self.game_state.halftime_started = True
        self.game_state.halftime_end_ts = current_time + int(HALFTIME_PAUSE_MIN * 60)
        self.game_state.paused = True

    def end_halftime(self) -> None:
        """End the break period and start the next period if available."""

        if not self.game_state.halftime_started:
            return

        self.game_state.halftime_started = False
        self.game_state.halftime_end_ts = None

        if self.game_state.current_period_index < self.game_state.period_count - 1:
            self.game_state.current_period_index += 1

        self.game_state.paused = False
        self.game_state.period_start_ts = now_ts()
        if self.game_state.game_start_ts is None:
            self.game_state.game_start_ts = self.game_state.period_start_ts

    # ------------------------------------------------------------------
    # Adjustment APIs
    # ------------------------------------------------------------------
    def add_time_adjustment(
        self,
        seconds: int,
        period_index: Optional[int] = None,
        apply_to_all: bool = False,
    ) -> None:
        """Apply a manual correction to one or more periods."""

        if seconds == 0:
            return

        self.game_state.ensure_timer_lists()
        if apply_to_all:
            targets = range(self.game_state.period_count)
        else:
            idx = (
                period_index
                if period_index is not None
                else self.game_state.current_period_index
            )
            idx = max(0, min(idx, self.game_state.period_count - 1))
            targets = [idx]

        for idx in targets:
            self.game_state.period_adjustments[idx] += seconds

        self.game_state.elapsed_adjustment = sum(
            self.game_state.period_adjustments[: self.game_state.period_count]
        )

    def add_stoppage_time(self, seconds: int, period_index: Optional[int] = None) -> None:
        """Track stoppage/injury time for the specified period."""

        if seconds == 0:
            return

        self.game_state.ensure_timer_lists()
        idx = (
            period_index
            if period_index is not None
            else self.game_state.current_period_index
        )
        idx = max(0, min(idx, self.game_state.period_count - 1))

        new_value = self.game_state.period_stoppage[idx] + seconds
        self.game_state.period_stoppage[idx] = max(0, new_value)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_timer_configuration(self) -> Dict[str, object]:
        """Return the current timer configuration for display purposes."""

        self.game_state.ensure_timer_lists()
        return {
            "game_length_seconds": self.game_state.game_length_seconds,
            "game_length_minutes": self.game_state.game_length_seconds // 60,
            "period_count": self.game_state.period_count,
            "period_lengths": self._get_period_lengths(),
            "total_stoppage_seconds": self._get_total_stoppage_seconds(),
            "total_adjustment_seconds": sum(
                self.game_state.period_adjustments[: self.game_state.period_count]
            ),
        }

    def get_period_summaries(self) -> List[Dict[str, int]]:
        """Return elapsed/adjustment data for each period."""

        self.game_state.ensure_timer_lists()
        summaries: List[Dict[str, int]] = []
        period_lengths = self._get_period_lengths()
        now = now_ts()

        for idx in range(self.game_state.period_count):
            running = 0
            if (
                idx == self.game_state.current_period_index
                and self.game_state.period_start_ts is not None
                and not self.game_state.paused
            ):
                running = int(now - self.game_state.period_start_ts)

            summaries.append(
                {
                    "index": idx,
                    "number": idx + 1,
                    "length_seconds": period_lengths[idx],
                    "elapsed_seconds": self.game_state.period_elapsed[idx] + running,
                    "adjustment_seconds": self.game_state.period_adjustments[idx],
                    "stoppage_seconds": self.game_state.period_stoppage[idx],
                }
            )

        return summaries

    def get_game_elapsed_seconds(self) -> int:
        """Get total elapsed game time including adjustments and stoppage."""

        if self.game_state.game_start_ts is None:
            return 0

        self.game_state.ensure_timer_lists()
        base_elapsed = self._get_base_elapsed_seconds()
        adjustments = sum(self.game_state.period_adjustments[: self.game_state.period_count])
        stoppage = self._get_total_stoppage_seconds()
        return max(0, base_elapsed + adjustments + stoppage)

    def get_remaining_seconds(self) -> int:
        """Get remaining game time including configured stoppage."""

        if self.game_state.game_start_ts is None:
            return self.game_state.game_length_seconds

        self.game_state.ensure_timer_lists()
        total_elapsed = self.get_game_elapsed_seconds()
        target = self.game_state.game_length_seconds + self._get_total_stoppage_seconds()
        return max(0, target - total_elapsed)

    def is_game_over(self) -> bool:
        """Return True when the configured game time has fully elapsed."""

        return self.get_remaining_seconds() == 0

    def get_half_info(self) -> Tuple[int, bool]:
        """Return the active period number and whether the timer is in a break."""

        period_number = min(self.game_state.current_period_index + 1, self.game_state.period_count)
        return (period_number, self.game_state.halftime_started)

    def should_suggest_halftime(self) -> bool:
        """Determine whether a period break should be suggested."""

        self.game_state.ensure_timer_lists()
        if self.game_state.halftime_started:
            return False

        if self.game_state.current_period_index >= self.game_state.period_count - 1:
            return False

        elapsed = self._get_current_period_elapsed_seconds(include_running=True)
        target = self._get_period_target_seconds(self.game_state.current_period_index)
        return elapsed >= target

    def get_halftime_remaining_seconds(self) -> Optional[int]:
        """Return remaining break seconds when in halftime."""

        if not self.game_state.halftime_started or self.game_state.halftime_end_ts is None:
            return None

        remaining = int(self.game_state.halftime_end_ts - now_ts())
        return max(0, remaining)

    def is_halftime_over(self) -> bool:
        """Return True when the current break period has finished."""

        remaining = self.get_halftime_remaining_seconds()
        return remaining is not None and remaining == 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_period_lengths(self) -> List[int]:
        base, remainder = divmod(self.game_state.game_length_seconds, self.game_state.period_count)
        lengths = [base] * self.game_state.period_count
        for idx in range(remainder):
            lengths[idx] += 1
        return lengths

    def _get_total_stoppage_seconds(self) -> int:
        return sum(self.game_state.period_stoppage[: self.game_state.period_count])

    def _get_base_elapsed_seconds(self) -> int:
        self.game_state.ensure_timer_lists()
        total = sum(self.game_state.period_elapsed[: self.game_state.period_count])
        if (
            self.game_state.period_start_ts is not None
            and not self.game_state.paused
        ):
            total += int(now_ts() - self.game_state.period_start_ts)
        elif total == 0 and self.game_state.game_start_ts is not None:
            total = max(0, int(now_ts() - self.game_state.game_start_ts))
        return total

    def _get_current_period_elapsed_seconds(self, *, include_running: bool) -> int:
        idx = min(self.game_state.current_period_index, self.game_state.period_count - 1)
        elapsed = self.game_state.period_elapsed[idx]
        if (
            include_running
            and self.game_state.period_start_ts is not None
            and not self.game_state.paused
        ):
            elapsed += int(now_ts() - self.game_state.period_start_ts)
        return elapsed

    def _get_period_target_seconds(self, period_index: int) -> int:
        self.game_state.ensure_timer_lists()
        lengths = self._get_period_lengths()
        adj = self.game_state.period_adjustments[period_index]
        stop = self.game_state.period_stoppage[period_index]
        return lengths[period_index] + adj + stop