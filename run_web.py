#!/usr/bin/env python3
"""
Main entry point for the Soccer Coach Sideline Timekeeper web application.

This script launches the Flask-based web server.
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.web_app import run_web_app

if __name__ == "__main__":
    # Run web app serving files from the project root
    project_root = os.path.dirname(__file__)
    run_web_app(static_folder=project_root)