"""
Utilities package for the Soccer Coach Sideline Timekeeper.

This package contains utility functions used throughout the application.
"""
from .time_utils import fmt_mmss, now_ts
from .constants import (
    APP_TITLE,
    GAME_LENGTH_MIN,
    EQUAL_TIME_TARGET_MIN,
    HALFTIME_PAUSE_MIN,
    POSITIONS,
    POS_SHORT_TO_FULL,
    DEFAULT_GAME_LENGTH_MIN,
    DEFAULT_PERIOD_COUNT,
    MIN_GAME_LENGTH_MIN,
    MAX_GAME_LENGTH_MIN,
    MIN_PERIOD_COUNT,
    MAX_PERIOD_COUNT,
    PERIOD_LABELS,
)

__all__ = [
    "fmt_mmss",
    "now_ts",
    "APP_TITLE",
    "GAME_LENGTH_MIN",
    "EQUAL_TIME_TARGET_MIN",
    "HALFTIME_PAUSE_MIN",
    "POSITIONS",
    "POS_SHORT_TO_FULL",
    "DEFAULT_GAME_LENGTH_MIN",
    "DEFAULT_PERIOD_COUNT",
    "MIN_GAME_LENGTH_MIN",
    "MAX_GAME_LENGTH_MIN",
    "MIN_PERIOD_COUNT",
    "MAX_PERIOD_COUNT",
    "PERIOD_LABELS",
]