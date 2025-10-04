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

# Field size configuration (flexible for different youth soccer formats)
MIN_FIELD_SIZE = 7   # Minimum players on field (e.g., 7v7 for U8-U10)
MAX_FIELD_SIZE = 11  # Maximum players on field (standard 11v11)
DEFAULT_FIELD_SIZE = 11  # Default to standard soccer

# Supported field sizes with common formats
SUPPORTED_FIELD_SIZES = [7, 9, 10, 11]

# Position configuration (deprecated - now dynamically configured per game)
POSITIONS = ["GK", "DF", "DF", "DF", "MF", "MF", "ST", "ST", "ST"]  # legacy 9-player default
POS_SHORT_TO_FULL = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "ST": "Striker"
}