"""
Web application module for the Soccer Coach Sideline Timekeeper.

This module contains the Flask web server that serves the HTML interface.
"""
import os
from flask import Flask, send_from_directory


def create_app(static_folder: str = ".") -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        static_folder: Directory to serve static files from
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, static_folder=static_folder, static_url_path="")

    @app.route("/")
    def index():
        """Serve the main HTML interface."""
        return send_from_directory(static_folder, "index.html")

    return app


def run_web_app(host: str = "127.0.0.1", port: int = 5000, static_folder: str = ".") -> None:
    """
    Run the web application.
    
    Args:
        host: Host address to bind to (default: localhost only)
        port: Port number to listen on
        static_folder: Directory containing static files (HTML, CSS, JS)
    """
    app = create_app(static_folder)
    # Bind only to localhost; Cloudflare Tunnel will connect locally if needed
    app.run(host=host, port=port)


if __name__ == "__main__":
    # Default to serving files from the project root when run directly
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    run_web_app(static_folder=project_root)