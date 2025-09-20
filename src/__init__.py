"""
Soccer Coach Sideline Timekeeper

A comprehensive application for managing soccer game timing, player rotations,
and ensuring equal playing time distribution.

This package provides both desktop (Tkinter) and web (Flask) interfaces
for coaches to manage their teams during games.
"""
from .models import Player, GameState
from .services import PersistenceService, TimerService
from .ui import create_tkinter_app, run_tkinter_app, create_app, run_web_app
from .utils import fmt_mmss, now_ts, APP_TITLE

__version__ = "2.0.0"
__author__ = "Soccer Coach Development Team"

__all__ = [
    "Player", "GameState", "PersistenceService", "TimerService",
    "create_tkinter_app", "run_tkinter_app", "create_app", "run_web_app",
    "fmt_mmss", "now_ts", "APP_TITLE"
]