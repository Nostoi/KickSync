"""
Constants for the Soccer Coach Sideline Timekeeper application.

This module contains configuration constants used throughout the application.
"""

# Application metadata
APP_TITLE = "Sideline Timekeeper"

# Game timing constants
GAME_LENGTH_MIN = 60
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