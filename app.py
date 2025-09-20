#!/usr/bin/env python3
"""
Legacy entry point for the Soccer Coach web application.

This file maintains backward compatibility. For new development,
use run_web.py or the src.ui.web_app module directly.
"""
import sys
import os

# Add the src directory to Python path for new modular structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Try using new modular structure
    from src.ui.web_app import run_web_app
    
    if __name__ == "__main__":
        # Run web app serving files from the project root
        project_root = os.path.dirname(__file__)
        run_web_app(host="127.0.0.1", port=5000, static_folder=project_root)
        
except ImportError:
    # Fallback to original implementation if new structure not available
    from flask import Flask, send_from_directory

    app = Flask(__name__, static_folder=".", static_url_path="")

    @app.route("/")
    def index():
        return send_from_directory(".", "index.html")

    if __name__ == "__main__":
        # Bind only to localhost; Cloudflare Tunnel will connect locally.
        app.run(host="127.0.0.1", port=7122)
