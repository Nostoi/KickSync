"""
Constants for the Soccer Coach Sideline Timekeeper application.

This module contains configuration constants used throughout the application.
"""

# Application metadata
APP_TITLE = "Sideline Timekeeper"

# Game timing defaults
DEFAULT_GAME_LENGTH_MIN = 60
DEFAULT_PERIOD_COUNT = 2
MIN_GAME_LENGTH_MIN = 10
MAX_GAME_LENGTH_MIN = 120
MIN_PERIOD_COUNT = 1
MAX_PERIOD_COUNT = 4

# Friendly labels for different period counts (used for UI hints)
PERIOD_LABELS = {
    1: "Full Time",
    2: "Half",
    3: "Third",
    4: "Quarter",
}

# Backward compatibility aliases – existing modules still import these names
GAME_LENGTH_MIN = DEFAULT_GAME_LENGTH_MIN

EQUAL_TIME_TARGET_MIN = 30
HALFTIME_PAUSE_MIN = 10.5

# Position configuration
POSITIONS = ["GK", "DF", "DF", "DF", "MF", "MF", "ST", "ST", "ST"]  # required on-field slots
POS_SHORT_TO_FULL = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "ST": "Striker"
}