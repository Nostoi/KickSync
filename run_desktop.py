#!/usr/bin/env python3
"""
Main entry point for the Soccer Coach Sideline Timekeeper desktop application.

This script launches the Tkinter-based desktop interface.
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.tkinter_app import run_tkinter_app

if __name__ == "__main__":
    run_tkinter_app()