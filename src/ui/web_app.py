"""
Web application module for the Soccer Coach Sideline Timekeeper.

This module contains the Flask web server that serves the HTML interface
and provides JSON API endpoints for the enhanced timer and analytics features.
"""
import os
import json
from typing import Dict, Any, Optional, List
from datetime import date

from flask import Flask, send_from_directory, jsonify, request

from ..models import GameState, Player, ContactInfo, MedicalInfo, PlayerStats, GameAttendance
from ..services import AnalyticsService, PersistenceService, TimerService
from ..services.player_service import PlayerService, PlayerValidationError
from ..utils import fmt_mmss, now_ts


class WebAppState:
    """Singleton state holder for the web application."""
    
    def __init__(self):
        self.game_state = GameState()
        self.timer_service = TimerService(self.game_state)
        self.analytics_service = AnalyticsService(self.game_state, self.timer_service)
        self.player_service = PlayerService()
        
    def reset_services(self):
        """Reset all services after state change."""
        self.timer_service = TimerService(self.game_state)
        self.analytics_service = AnalyticsService(self.game_state, self.timer_service)


# Global state instance
app_state = WebAppState()


def create_app(static_folder: str = ".") -> Flask:
    """
    Create and configure the Flask application with API endpoints.
    
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

    # ==================== API Endpoints ==================== #

    @app.route("/api/state", methods=["GET"])
    def get_state():
        """Get current game state and analytics."""
        try:
            config = app_state.timer_service.get_timer_configuration()
            report = app_state.analytics_service.generate_game_report()
            
            # Timer information
            elapsed_seconds = app_state.timer_service.get_game_elapsed_seconds()
            remaining_seconds = app_state.timer_service.get_remaining_seconds()
            period_number, in_break = app_state.timer_service.get_half_info()
            summaries = app_state.timer_service.get_period_summaries()
            
            # Player information
            players_data = []
            for name, player in app_state.game_state.roster.items():
                current_time = now_ts()
                total_seconds = player.total_seconds + player.current_stint_seconds(current_time)
                
                # Find analytics for this player
                player_summary = next((p for p in report.players if p.name == name), None)
                
                players_data.append({
                    "name": player.name,
                    "number": player.number,
                    "position": player.position,
                    "preferred_positions": player.preferred,
                    "on_field": player.on_field,
                    "total_seconds": total_seconds,
                    "fairness": player_summary.fairness if player_summary else "ok",
                    "target_seconds": player_summary.target_seconds if player_summary else 0,
                    "delta_seconds": player_summary.delta_seconds if player_summary else 0,
                })
            
            return jsonify({
                "success": True,
                "game_state": {
                    "game_started": app_state.game_state.game_start_ts is not None,
                    "paused": app_state.game_state.paused,
                    "elapsed_seconds": elapsed_seconds,
                    "remaining_seconds": remaining_seconds,
                    "target_seconds": config["game_length_seconds"] + config["total_stoppage_seconds"],
                    "period_number": period_number,
                    "period_count": config["period_count"],
                    "in_break": in_break,
                    "total_stoppage_seconds": config["total_stoppage_seconds"],
                    "total_adjustment_seconds": config["total_adjustment_seconds"],
                },
                "periods": summaries,
                "players": players_data,
                "analytics": {
                    "roster_size": report.roster_size,
                    "elapsed_seconds": report.elapsed_seconds,
                    "target_seconds_total": report.target_seconds_total,
                    "regulation_seconds": report.regulation_seconds,
                    "stoppage_seconds": report.stoppage_seconds,
                    "adjustment_seconds": report.adjustment_seconds,
                    "target_seconds_per_player": report.target_seconds_per_player,
                    "average_seconds": report.average_seconds,
                    "median_seconds": report.median_seconds,
                    "min_seconds": report.min_seconds,
                    "max_seconds": report.max_seconds,
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/timer/start", methods=["POST"])
    def start_timer():
        """Start the game timer."""
        try:
            app_state.timer_service.start_game()
            return jsonify({"success": True, "message": "Game started"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/timer/pause", methods=["POST"])
    def pause_timer():
        """Pause the game timer."""
        try:
            app_state.timer_service.pause_game()
            return jsonify({"success": True, "message": "Game paused"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/timer/halftime", methods=["POST"])
    def start_halftime():
        """Start halftime break."""
        try:
            app_state.timer_service.start_halftime()
            return jsonify({"success": True, "message": "Halftime started"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/timer/configure", methods=["POST"])
    def configure_timer():
        """Configure game length and period count."""
        try:
            data = request.get_json()
            minutes = data.get("minutes", 60)
            periods = data.get("periods", 2)
            
            app_state.timer_service.configure_game(
                game_length_minutes=minutes,
                period_count=periods
            )
            return jsonify({"success": True, "message": "Timer configured"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/timer/stoppage", methods=["POST"])
    def add_stoppage_time():
        """Add stoppage time to current or specified period."""
        try:
            data = request.get_json()
            seconds = data.get("seconds", 0)
            period_index = data.get("period_index")  # Optional
            
            app_state.timer_service.add_stoppage_time(
                seconds, period_index=period_index
            )
            return jsonify({"success": True, "message": f"Added {seconds}s stoppage time"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/timer/adjustment", methods=["POST"])
    def add_time_adjustment():
        """Add time adjustment to current or specified period."""
        try:
            data = request.get_json()
            seconds = data.get("seconds", 0)
            period_index = data.get("period_index")  # Optional
            apply_to_all = data.get("apply_to_all", False)
            
            app_state.timer_service.add_time_adjustment(
                seconds, 
                period_index=period_index,
                apply_to_all=apply_to_all
            )
            return jsonify({"success": True, "message": f"Added {seconds}s time adjustment"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/roster", methods=["POST"])
    def update_roster():
        """Update the roster with new players."""
        try:
            data = request.get_json()
            players_data = data.get("players", [])
            
            roster = {}
            for player_data in players_data:
                # Handle backward compatibility for simple player data
                if isinstance(player_data, dict) and "to_dict" not in player_data:
                    # Create Player from dictionary data
                    try:
                        player = Player.from_dict(player_data) if "contact_info" in player_data or "medical_info" in player_data else Player(
                            name=player_data["name"],
                            number=player_data.get("number", ""),
                            preferred=",".join(player_data.get("preferred", [])) if isinstance(player_data.get("preferred"), list) else player_data.get("preferred", "")
                        )
                    except Exception:
                        # Fallback to simple player creation
                        player = Player(
                            name=player_data["name"],
                            number=player_data.get("number", ""),
                            preferred=",".join(player_data.get("preferred", [])) if isinstance(player_data.get("preferred"), list) else player_data.get("preferred", "")
                        )
                else:
                    # Handle simple format for backward compatibility
                    player = Player(
                        name=player_data["name"],
                        number=player_data.get("number", ""),
                        preferred=",".join(player_data.get("preferred", [])) if isinstance(player_data.get("preferred"), list) else player_data.get("preferred", "")
                    )
                
                roster[player.name] = player
            
            app_state.game_state = GameState(roster=roster)
            app_state.reset_services()
            
            return jsonify({"success": True, "message": f"Roster updated with {len(roster)} players"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    # ==================== Player Management Endpoints ==================== #

    @app.route("/api/players", methods=["GET"])
    def get_players():
        """Get all players with enhanced information."""
        try:
            players_data = []
            for player in app_state.game_state.roster.values():
                player_dict = player.to_dict()
                # Add computed fields
                player_dict["age"] = player.age()
                player_dict["attendance_rate"] = player.get_attendance_rate()
                players_data.append(player_dict)
            
            return jsonify({
                "success": True,
                "players": players_data,
                "count": len(players_data)
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players", methods=["POST"])
    def create_player():
        """Create a new player."""
        try:
            data = request.get_json()
            
            # Extract basic info
            name = data.get("name", "").strip()
            number = data.get("number", "").strip()
            preferred_positions = data.get("preferred_positions", [])
            
            # Extract optional enhanced fields
            date_of_birth = None
            if data.get("date_of_birth"):
                try:
                    date_of_birth = date.fromisoformat(data["date_of_birth"])
                except ValueError:
                    pass
            
            contact_info = ContactInfo.from_dict(data.get("contact_info", {}))
            medical_info = MedicalInfo.from_dict(data.get("medical_info", {}))
            notes = data.get("notes")
            
            # Create player using PlayerService for validation
            player = app_state.player_service.create_player(
                name=name,
                number=number if number else None,
                preferred_positions=preferred_positions,
                date_of_birth=date_of_birth,
                contact_info=contact_info,
                medical_info=medical_info,
                notes=notes
            )
            
            # Check if player already exists
            if player.name in app_state.game_state.roster:
                return jsonify({"success": False, "error": f"Player '{player.name}' already exists"}), 409
            
            # Add to roster
            app_state.game_state.roster[player.name] = player
            
            return jsonify({
                "success": True,
                "message": f"Player '{player.name}' created successfully",
                "player": player.to_dict()
            })
        except PlayerValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/<player_name>", methods=["GET"])
    def get_player(player_name: str):
        """Get detailed information for a specific player."""
        try:
            if player_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            player = app_state.game_state.roster[player_name]
            player_dict = player.to_dict()
            
            # Add computed fields
            player_dict["age"] = player.age()
            player_dict["attendance_rate"] = player.get_attendance_rate()
            player_dict["summary"] = app_state.player_service.get_player_summary(player)
            
            return jsonify({
                "success": True,
                "player": player_dict
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/<player_name>", methods=["PUT"])
    def update_player(player_name: str):
        """Update an existing player."""
        try:
            if player_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            data = request.get_json()
            current_player = app_state.game_state.roster[player_name]
            
            # Create updated player (preserve game state fields)
            updated_player = Player.from_dict({
                **data,
                # Preserve current game state
                "total_seconds": current_player.total_seconds,
                "on_field": current_player.on_field,
                "position": current_player.position,
                "stint_start_ts": current_player.stint_start_ts,
            })
            
            # Validate the updated player
            errors = app_state.player_service.validate_player_data(updated_player)
            if errors:
                return jsonify({"success": False, "error": "; ".join(errors)}), 400
            
            # Handle name change (need to update roster key)
            if updated_player.name != player_name:
                if updated_player.name in app_state.game_state.roster:
                    return jsonify({"success": False, "error": f"Player '{updated_player.name}' already exists"}), 409
                del app_state.game_state.roster[player_name]
            
            app_state.game_state.roster[updated_player.name] = updated_player
            
            return jsonify({
                "success": True,
                "message": f"Player updated successfully",
                "player": updated_player.to_dict()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/<player_name>", methods=["DELETE"])
    def delete_player(player_name: str):
        """Delete a player from the roster."""
        try:
            if player_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            player = app_state.game_state.roster[player_name]
            
            # Don't allow deletion of players currently on field
            if player.on_field:
                return jsonify({"success": False, "error": "Cannot delete player currently on field"}), 409
            
            del app_state.game_state.roster[player_name]
            
            return jsonify({
                "success": True,
                "message": f"Player '{player_name}' deleted successfully"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/<player_name>/stats", methods=["POST"])
    def update_player_stats(player_name: str):
        """Update player statistics for a game."""
        try:
            if player_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            data = request.get_json()
            player = app_state.game_state.roster[player_name]
            
            # Update statistics
            app_state.player_service.update_player_stats(
                player,
                goals=data.get("goals", 0),
                assists=data.get("assists", 0),
                shots=data.get("shots", 0),
                saves=data.get("saves", 0),
                fouls_committed=data.get("fouls_committed", 0),
                fouls_received=data.get("fouls_received", 0),
                yellow_cards=data.get("yellow_cards", 0),
                red_cards=data.get("red_cards", 0)
            )
            
            # Record game participation if provided
            if data.get("minutes_played") is not None:
                app_state.player_service.record_game_participation(
                    player,
                    minutes_played=data["minutes_played"],
                    started=data.get("started", False)
                )
            
            return jsonify({
                "success": True,
                "message": f"Statistics updated for {player_name}",
                "statistics": player.statistics.to_dict()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/<player_name>/attendance", methods=["POST"])
    def mark_player_attendance(player_name: str):
        """Mark attendance for a player."""
        try:
            if player_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            data = request.get_json()
            player = app_state.game_state.roster[player_name]
            
            # Parse date
            game_date = date.today()
            if data.get("date"):
                try:
                    game_date = date.fromisoformat(data["date"])
                except ValueError:
                    return jsonify({"success": False, "error": "Invalid date format"}), 400
            
            present = data.get("present", True)
            reason = data.get("reason") if not present else None
            
            app_state.player_service.mark_attendance(player, game_date, present, reason)
            
            return jsonify({
                "success": True,
                "message": f"Attendance marked for {player_name}",
                "attendance_rate": player.get_attendance_rate()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/<player_name>/skills", methods=["POST"])
    def update_player_skills(player_name: str):
        """Update player skill ratings."""
        try:
            if player_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            data = request.get_json()
            player = app_state.game_state.roster[player_name]
            
            # Update skill ratings
            skill_ratings = data.get("skill_ratings", {})
            for position, rating in skill_ratings.items():
                try:
                    player.set_skill_rating(position, rating)
                except ValueError as e:
                    return jsonify({"success": False, "error": str(e)}), 400
            
            return jsonify({
                "success": True,
                "message": f"Skill ratings updated for {player_name}",
                "skill_ratings": player.skill_ratings
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/import", methods=["POST"])
    def import_players():
        """Import players from JSON data."""
        try:
            data = request.get_json()
            players_data = data.get("players", [])
            
            if not players_data:
                return jsonify({"success": False, "error": "No player data provided"}), 400
            
            # Create temporary file-like structure for PlayerService
            import tempfile
            import json as json_module
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json_module.dump({"players": players_data}, f, indent=2)
                temp_file = f.name
            
            try:
                imported_players = app_state.player_service.import_player_data(temp_file)
                
                # Handle conflicts
                conflicts = []
                added = []
                
                merge_strategy = data.get("merge_strategy", "skip")  # "skip", "overwrite", "error"
                
                for player in imported_players:
                    if player.name in app_state.game_state.roster:
                        conflicts.append(player.name)
                        if merge_strategy == "overwrite":
                            # Preserve current game state
                            current = app_state.game_state.roster[player.name]
                            player.total_seconds = current.total_seconds
                            player.on_field = current.on_field
                            player.position = current.position
                            player.stint_start_ts = current.stint_start_ts
                            app_state.game_state.roster[player.name] = player
                            added.append(player.name)
                        elif merge_strategy == "error":
                            return jsonify({
                                "success": False, 
                                "error": f"Player '{player.name}' already exists"
                            }), 409
                        # "skip" - do nothing
                    else:
                        app_state.game_state.roster[player.name] = player
                        added.append(player.name)
                
                return jsonify({
                    "success": True,
                    "message": f"Imported {len(added)} players successfully",
                    "added": added,
                    "conflicts": conflicts,
                    "total_imported": len(imported_players)
                })
            finally:
                os.unlink(temp_file)
                
        except PlayerValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/export", methods=["GET"])
    def export_players():
        """Export all players to JSON format."""
        try:
            players = list(app_state.game_state.roster.values())
            
            export_data = {
                "exported_at": date.today().isoformat(),
                "player_count": len(players),
                "players": [player.to_dict() for player in players]
            }
            
            return jsonify({
                "success": True,
                "export_data": export_data
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/players/recommendations", methods=["POST"])
    def get_position_recommendations():
        """Get position recommendations for players."""
        try:
            data = request.get_json()
            available_positions = data.get("available_positions", [])
            
            if not available_positions:
                return jsonify({"success": False, "error": "No positions specified"}), 400
            
            recommendations = {}
            for player in app_state.game_state.roster.values():
                if not player.on_field:  # Only recommend for players not on field
                    player_recs = app_state.player_service.get_position_recommendations(
                        player, available_positions
                    )
                    recommendations[player.name] = [
                        {"position": pos, "score": score} for pos, score in player_recs
                    ]
            
            return jsonify({
                "success": True,
                "recommendations": recommendations
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ==================== End Player Management Endpoints ==================== #

    @app.route("/api/substitution", methods=["POST"])
    def make_substitution():
        """Make a player substitution."""
        try:
            data = request.get_json()
            out_name = data.get("out_name")
            in_name = data.get("in_name")
            
            if not out_name or not in_name:
                return jsonify({"success": False, "error": "Both out_name and in_name required"}), 400
            
            if out_name not in app_state.game_state.roster or in_name not in app_state.game_state.roster:
                return jsonify({"success": False, "error": "Player not found"}), 404
            
            out_player = app_state.game_state.roster[out_name]
            in_player = app_state.game_state.roster[in_name]
            
            if not out_player.on_field:
                return jsonify({"success": False, "error": f"{out_name} is not on field"}), 400
            if in_player.on_field:
                return jsonify({"success": False, "error": f"{in_name} is already on field"}), 400
            
            # Perform substitution
            current_time = now_ts()
            out_player.sub_off(current_time)
            in_player.sub_on(current_time, out_player.position)
            
            return jsonify({"success": True, "message": f"Substituted {out_name} for {in_name}"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/save", methods=["POST"])
    def save_game():
        """Save current game state."""
        try:
            # For web version, we'll return the JSON data for client-side saving
            game_data = PersistenceService.serialize_game_state(app_state.game_state)
            return jsonify({"success": True, "data": game_data})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/load", methods=["POST"])
    def load_game():
        """Load game state from uploaded JSON."""
        try:
            data = request.get_json()
            game_data = data.get("game_data")
            
            if not game_data:
                return jsonify({"success": False, "error": "No game data provided"}), 400
            
            app_state.game_state = PersistenceService.deserialize_game_state(game_data)
            app_state.reset_services()
            
            return jsonify({"success": True, "message": "Game state loaded successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/analytics/report", methods=["GET"])
    def get_analytics_report():
        """Get detailed analytics report."""
        try:
            report = app_state.analytics_service.generate_game_report()
            
            return jsonify({
                "success": True,
                "report": {
                    "roster_size": report.roster_size,
                    "elapsed_seconds": report.elapsed_seconds,
                    "target_seconds_total": report.target_seconds_total,
                    "regulation_seconds": report.regulation_seconds,
                    "stoppage_seconds": report.stoppage_seconds,
                    "adjustment_seconds": report.adjustment_seconds,
                    "target_seconds_per_player": report.target_seconds_per_player,
                    "average_seconds": report.average_seconds,
                    "median_seconds": report.median_seconds,
                    "min_seconds": report.min_seconds,
                    "max_seconds": report.max_seconds,
                    "players": [
                        {
                            "name": p.name,
                            "number": p.number,
                            "preferred_positions": p.preferred_positions,
                            "on_field": p.on_field,
                            "position": p.position,
                            "cumulative_seconds": p.cumulative_seconds,
                            "target_seconds": p.target_seconds,
                            "delta_seconds": p.delta_seconds,
                            "target_share": p.target_share,
                            "fairness": p.fairness,
                        }
                        for p in report.players
                    ]
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

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
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    # Default to serving files from the project root when run directly
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    run_web_app(static_folder=project_root)