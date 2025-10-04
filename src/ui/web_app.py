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
from ..models.formation import Formation, FormationType, FieldPosition, Position
from ..services import AnalyticsService, PersistenceService, TimerService
from ..services.player_service import PlayerService, PlayerValidationError
from ..services.strategy_service import StrategyService
from ..services.formation_validator import FormationValidationService, LineupEdgeCaseHandler
from ..utils import fmt_mmss, now_ts


class WebAppState:
    """
    Clean architecture state holder for the web application.
    
    Uses dependency injection and service factory following SOLID principles.
    """
    
    def __init__(self):
        from ..services.service_factory import ServiceFactory
        from ..services.strategy_service import StrategyService
        from ..services.game_commands import GameCommandManager
        
        self.game_state = GameState()
        # Ensure timer lists are properly initialized
        self.game_state.ensure_timer_lists()
        self.service_factory = ServiceFactory()
        
        # Create services using factory with proper dependency injection
        services = self.service_factory.create_complete_service_suite(self.game_state)
        self.timer_service = services['timer']
        self.analytics_service = services['analytics']
        self.player_service = services['player']
        self.persistence_service = services['persistence']
        
        # Additional services not in factory yet
        self.strategy_service = StrategyService(self.game_state)
        self.command_manager = GameCommandManager()
        
        # Formation validation service for edge case handling
        self.formation_validator = FormationValidationService(
            self.game_state.roster,
            self.strategy_service._formations
        )
        self.lineup_edge_handler = LineupEdgeCaseHandler(self.formation_validator)
        
    def reset_services(self):
        """Reset all services after state change using clean architecture."""
        services = self.service_factory.create_complete_service_suite(self.game_state)
        self.timer_service = services['timer']
        self.analytics_service = services['analytics']
        self.strategy_service = StrategyService(self.game_state)
        # Keep command history across resets for consistency


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
        response = send_from_directory(static_folder, "index.html")
        # Add cache-busting headers for development
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # ==================== API Endpoints ==================== #

    def _build_timer_data(config: dict) -> dict:
        """Build timer information following SRP."""
        elapsed_seconds = app_state.timer_service.get_game_elapsed_seconds()
        remaining_seconds = app_state.timer_service.get_remaining_seconds()
        period_number, in_break = app_state.timer_service.get_half_info()
        
        return {
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
            "field_size": app_state.game_state.field_size,
        }
    
    def _build_player_data(report) -> List[dict]:
        """Build player information following SRP."""
        players_data = []
        current_time = now_ts()
        
        for name, player in app_state.game_state.roster.items():
            total_seconds = player.total_seconds + player.current_stint_seconds(current_time)
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
        
        return players_data
    
    def _build_analytics_data(report) -> dict:
        """Build analytics information following SRP."""
        return {
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

    @app.route("/api/state", methods=["GET"])
    def get_state():
        """Get current game state and analytics - clean, focused method."""
        try:
            config = app_state.timer_service.get_timer_configuration()
            report = app_state.analytics_service.generate_game_report()
            summaries = app_state.timer_service.get_period_summaries()
            
            return jsonify({
                "success": True,
                "game_state": _build_timer_data(config),
                "periods": summaries,
                "players": _build_player_data(report),
                "analytics": _build_analytics_data(report)
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/timer/start", methods=["POST"])
    def start_timer():
        """Start the game timer with comprehensive lineup validation."""
        try:
            # Add debug logging
            print(f"DEBUG: Timer start request received. Content-Type: {request.content_type}")
            print(f"DEBUG: Request data: {request.get_data()}")
            
            # Check if game is already active
            if app_state.game_state.is_active():
                return jsonify({
                    "success": False,
                    "error": "Game is already in progress",
                    "suggestions": ["Pause or end the current game before starting a new one"]
                }), 400
            
            # Get optional formation name from request - handle various request formats
            data = {}
            try:
                # Handle empty JSON body with Content-Type: application/json
                if request.content_type == 'application/json':
                    if hasattr(request, 'content_length') and request.content_length and request.content_length > 0:
                        # Has actual content
                        data = request.get_json() or {}
                    else:
                        # Empty body with JSON content type - this is the problematic case
                        print("DEBUG: Empty JSON body received - treating as empty dict")
                        data = {}
                else:
                    # No JSON content type - also acceptable for this endpoint
                    data = {}
            except Exception as e:
                print(f"DEBUG: Request parsing error: {e}")
                # Force treat as empty data if parsing fails
                data = {}
            
            formation_name = data.get("formation_name")
            
            # Pre-game validation checklist
            validation_errors = []
            warnings = []
            
            # Check if we have any players in roster
            print(f"DEBUG: Roster check - roster exists: {app_state.game_state.roster is not None}")
            if app_state.game_state.roster:
                print(f"DEBUG: Roster size: {len(app_state.game_state.roster)}")
            
            if not app_state.game_state.roster:
                validation_errors.append("No players in roster")
                print("DEBUG: Validation error - No players in roster")
            elif len(app_state.game_state.roster) < app_state.game_state.field_size:
                validation_errors.append(f"Need at least {app_state.game_state.field_size} players, only {len(app_state.game_state.roster)} in roster")
                print(f"DEBUG: Validation error - Not enough players: {len(app_state.game_state.roster)}")
            
            # Validate starting lineup if formation is specified
            formation_valid = True
            if formation_name:
                try:
                    formation = app_state.strategy_service.get_formation(formation_name)
                    if not formation:
                        validation_errors.append(f"Formation '{formation_name}' not found")
                        formation_valid = False
                    else:
                        # Validate formation for game start
                        validation_result = app_state.formation_validator.validate_formation(
                            formation, 
                            is_game_active=False  # We're about to start
                        )
                except Exception as e:
                    print(f"DEBUG: Formation validation error: {e}")
                    validation_errors.append(f"Formation validation failed: {str(e)}")
                    formation_valid = False
                
                if formation_valid and formation:
                    if not validation_result.is_valid:
                        validation_errors.extend(validation_result.errors)
                        formation_valid = False
                    
                    # Check completeness with error handling
                    if formation_valid:
                        try:
                            assigned, total, missing_types = app_state.formation_validator.get_formation_completeness(formation)
                            
                            if assigned < total:
                                validation_errors.append(f"Starting lineup incomplete: {assigned}/{total} positions filled")
                                formation_valid = False
                            
                            if missing_types:
                                validation_errors.append(f"Missing critical positions: {', '.join(missing_types)}")
                                formation_valid = False
                                
                            # Add warnings for sub-optimal assignments
                            if formation_valid:
                                for pos in formation.positions:
                                    if pos.player_name and pos.player_name in app_state.game_state.roster:
                                        player = app_state.game_state.roster[pos.player_name]
                                        if hasattr(player, 'preferred_positions') and player.preferred_positions:
                                            try:
                                                preferred_codes = [p.upper() for p in player.preferred_list()]
                                                pos_code = pos.position_code.value.upper()
                                                
                                                if pos_code not in preferred_codes:
                                                    warnings.append(f"{pos.player_name} playing out of preferred position ({pos_code})")
                                            except Exception as e:
                                                print(f"DEBUG: Warning generation error: {e}")
                        except Exception as e:
                            print(f"DEBUG: Formation completeness check error: {e}")
                            warnings.append(f"Could not fully validate formation: {str(e)}")
            
            # If we have validation errors, return them
            if validation_errors:
                print(f"DEBUG: Returning validation errors: {validation_errors}")
                return jsonify({
                    "success": False,
                    "error": "Cannot start game - lineup validation failed",
                    "validation_errors": validation_errors,
                    "warnings": warnings,
                    "suggestions": [
                        f"Ensure you have at least {app_state.game_state.field_size} players in your roster",
                        "Complete your starting formation with all positions filled",
                        "Assign a goalkeeper to your lineup",
                        "Check that player assignments are valid"
                    ]
                }), 400
            
            # Start the game using Command pattern
            try:
                from ..services.game_commands import StartGameCommand
                command = StartGameCommand(app_state.game_state)
                
                success = app_state.command_manager.execute_command(command)
                if success:
                    response = {
                        "success": True, 
                        "message": "Game timer started successfully"
                    }
                    
                    # Add warnings if any
                    if warnings:
                        response["warnings"] = warnings
                    
                    # Add formation info if provided
                    if formation_name and formation_valid:
                        response["formation"] = formation_name
                        response["message"] += f" with formation '{formation_name}'"
                    
                    return jsonify(response)
                else:
                    return jsonify({
                        "success": False, 
                        "error": "Failed to start game timer",
                        "suggestions": ["Check game state and try again"]
                    }), 400
            except Exception as e:
                print(f"DEBUG: Command execution error: {e}")
                return jsonify({
                    "success": False, 
                    "error": f"Game command failed: {str(e)}",
                    "suggestions": ["Check game state and try again"]
                }), 500
                
        except Exception as e:
            import traceback
            print(f"DEBUG: Unexpected error in start_timer: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return jsonify({
                "success": False, 
                "error": f"Unexpected error starting game: {str(e)}",
                "suggestions": ["Please try again or contact support if the problem persists"]
            }), 500

    @app.route("/api/timer/pause", methods=["POST"])
    def pause_timer():
        """Pause the game timer using Command pattern."""
        try:
            from ..services.game_commands import PauseGameCommand
            command = PauseGameCommand(app_state.game_state)
            
            success = app_state.command_manager.execute_command(command)
            if success:
                return jsonify({"success": True, "message": "Game timer paused"})
            else:
                return jsonify({"success": False, "error": "Failed to pause timer"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/undo", methods=["POST"])
    def undo_action():
        """Undo the last action using Command pattern."""
        try:
            success = app_state.command_manager.undo()
            if success:
                return jsonify({"success": True, "message": "Action undone"})
            else:
                return jsonify({"success": False, "message": "Nothing to undo"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/redo", methods=["POST"])
    def redo_action():
        """Redo the next action using Command pattern."""
        try:
            success = app_state.command_manager.redo()
            if success:
                return jsonify({"success": True, "message": "Action redone"})
            else:
                return jsonify({"success": False, "message": "Nothing to redo"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/command-history", methods=["GET"])
    def get_command_history():
        """Get command history for UI display."""
        try:
            history = app_state.command_manager.get_command_history()
            return jsonify({
                "success": True,
                "history": history,
                "can_undo": app_state.command_manager.can_undo(),
                "can_redo": app_state.command_manager.can_redo()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

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
            field_size = data.get("field_size", 11)  # Default to 11 for backward compatibility
            
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
            
            app_state.game_state = GameState(roster=roster, field_size=field_size)
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
            roster = app_state.game_state.roster if app_state.game_state else {}
            
            for player in roster.values():
                try:
                    player_dict = player.to_dict()
                    # Add computed fields safely
                    try:
                        player_dict["age"] = player.age()
                    except Exception:
                        player_dict["age"] = None
                    
                    try:
                        player_dict["attendance_rate"] = player.get_attendance_rate()
                    except Exception:
                        player_dict["attendance_rate"] = 100.0
                    
                    players_data.append(player_dict)
                except Exception as player_error:
                    # Skip problematic players but continue processing
                    print(f"Error processing player: {player_error}")
                    continue
            
            return jsonify({
                "success": True,
                "players": players_data,
                "count": len(players_data)
            })
        except Exception as e:
            print(f"Error in get_players: {e}")
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
            
            # Save the position before ending the stint
            position_to_fill = out_player.position
            
            # End the outgoing player's stint
            out_player.end_stint(current_time)
            
            # Start the incoming player's stint in the vacated position
            in_player.position = position_to_fill
            in_player.start_stint(current_time)
            
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

    @app.route("/api/analytics/export", methods=["GET"])
    def export_analytics_report():
        """Export detailed analytics report as CSV."""
        try:
            csv_content = app_state.analytics_service.export_game_report_csv()
            
            # Create response with proper headers for CSV download
            from flask import Response
            return Response(
                csv_content,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=game_report_{app_state.analytics_service.generate_game_report().generated_ts}.csv"
                }
            )
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ---------- Formation/Strategy API ---------- #
    
    @app.route("/api/formations", methods=["GET"])
    def get_formations():
        """Get all formations."""
        try:
            formations = app_state.strategy_service.list_formations()
            return jsonify({
                "success": True,
                "formations": [formation.to_dict() for formation in formations]
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/formations/templates", methods=["GET"])
    def get_formation_templates():
        """Get formation templates."""
        try:
            templates = app_state.strategy_service.get_formation_templates()
            return jsonify({
                "success": True,
                "templates": [template.to_dict() for template in templates]
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/formations", methods=["POST"])
    def create_formation():
        """Create a new formation with comprehensive validation."""
        try:
            data = request.json
            
            # Basic input validation
            name = data.get("name", "").strip()
            if not name:
                error_result = app_state.lineup_edge_handler.handle_formation_creation_error(
                    "empty_name"
                )
                return jsonify(error_result), 400
            
            # Validate formation type
            formation_type_str = data.get("formation_type", "4-4-2")
            try:
                formation_type = FormationType(formation_type_str)
            except ValueError:
                return jsonify({
                    "success": False, 
                    "error": f"Invalid formation type: {formation_type_str}",
                    "suggestions": ["Use a standard formation type like 4-4-2, 4-3-3, or 3-5-2"]
                }), 400
            
            # Parse positions with validation
            positions_data = data.get("positions", [])
            positions = []
            
            try:
                for i, pos_data in enumerate(positions_data):
                    x = pos_data.get("x", 0)
                    y = pos_data.get("y", 0)
                    
                    # Validate coordinates
                    if not (0 <= x <= 100) or not (0 <= y <= 100):
                        return jsonify({
                            "success": False,
                            "error": f"Position {i+1} has invalid coordinates ({x}, {y})",
                            "suggestions": ["Ensure all positions are within field boundaries (0-100)"]
                        }), 400
                    
                    position = FieldPosition(
                        x=x,
                        y=y,
                        position_code=Position(pos_data.get("position_code", "MID"))
                    )
                    
                    # Handle player assignments if provided
                    if pos_data.get("player_name"):
                        player_name = pos_data.get("player_name").strip()
                        player_number = pos_data.get("player_number", 0)
                        
                        # Validate player exists in roster
                        if player_name not in app_state.game_state.roster:
                            return jsonify({
                                "success": False,
                                "error": f"Player '{player_name}' not found in roster",
                                "suggestions": ["Add the player to your roster first"]
                            }), 400
                        
                        position.player_name = player_name
                        position.player_number = player_number
                    
                    positions.append(position)
                    
            except ValueError as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid position data: {str(e)}",
                    "suggestions": ["Check that all position codes are valid"]
                }), 400
            
            description = data.get("description", "")
            
            # Create formation object for validation
            from ..models.formation import Formation
            formation = Formation(
                name=name,
                formation_type=formation_type,
                positions=positions,
                description=description
            )
            
            # Comprehensive validation using our validator
            validation_result = app_state.formation_validator.validate_formation(
                formation, 
                is_update=False,
                is_game_active=app_state.game_state.is_active()
            )
            
            if not validation_result.is_valid:
                return jsonify({
                    "success": False,
                    "errors": validation_result.errors,
                    "suggestions": [
                        f"Ensure formation has exactly {app_state.game_state.field_size} positions",
                        "Include exactly 1 goalkeeper",
                        "Check that all positions are properly placed",
                        "Verify player assignments are valid"
                    ]
                }), 400
            
            # Save formation using strategy service
            try:
                saved_formation = app_state.strategy_service.create_formation(
                    name, formation_type, positions, description
                )
                
                # Update validator's formation list
                app_state.formation_validator.existing_formations[name] = saved_formation
                
                return jsonify({
                    "success": True,
                    "formation": saved_formation.to_dict(),
                    "message": f"Formation '{name}' created successfully"
                })
                
            except Exception as save_error:
                error_result = app_state.lineup_edge_handler.handle_formation_creation_error(
                    "permission_error" if "permission" in str(save_error).lower() else "network_error",
                    str(save_error)
                )
                return jsonify(error_result), 500
            
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": f"Unexpected error: {str(e)}",
                "suggestions": ["Please try again or contact support if the problem persists"]
            }), 500

    @app.route("/api/formations/<formation_name>", methods=["GET"])
    def get_formation(formation_name):
        """Get a specific formation."""
        try:
            formation = app_state.strategy_service.get_formation(formation_name)
            if not formation:
                return jsonify({"success": False, "error": "Formation not found"}), 404
            
            return jsonify({
                "success": True,
                "formation": formation.to_dict()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/formations/<formation_name>", methods=["DELETE"])
    def delete_formation(formation_name):
        """Delete a formation."""
        try:
            success = app_state.strategy_service.delete_formation(formation_name)
            if not success:
                return jsonify({"success": False, "error": "Formation not found"}), 404
            
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/formations/from-template", methods=["POST"])
    def create_from_template():
        """Create formation from template."""
        try:
            data = request.json
            
            template_type_str = data.get("template_type", "")
            name = data.get("name", "").strip()
            
            if not name:
                return jsonify({"success": False, "error": "Formation name is required"}), 400
            
            try:
                template_type = FormationType(template_type_str)
            except ValueError:
                return jsonify({"success": False, "error": f"Invalid template type: {template_type_str}"}), 400
            
            formation = app_state.strategy_service.create_from_template(template_type, name)
            if not formation:
                return jsonify({"success": False, "error": "Template not found"}), 404
            
            return jsonify({
                "success": True,
                "formation": formation.to_dict()
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/formations/suggest", methods=["POST"])
    def suggest_formation():
        """Suggest optimal formation based on available players."""
        try:
            available_players = list(app_state.game_state.roster.values())
            suggested = app_state.strategy_service.suggest_optimal_formation(
                available_players, 
                app_state.game_state.field_size
            )
            
            if not suggested:
                return jsonify({
                    "success": False, 
                    "error": f"Unable to suggest formation. Need at least {app_state.game_state.field_size} players."
                }), 400
            
            return jsonify({
                "success": True,
                "formation": suggested.to_dict()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/formations/<formation_name>/assign", methods=["POST"])
    def assign_players_to_formation(formation_name):
        """Assign players to formation positions with comprehensive validation."""
        try:
            formation = app_state.strategy_service.get_formation(formation_name)
            if not formation:
                return jsonify({
                    "success": False, 
                    "error": "Formation not found",
                    "suggestions": ["Check the formation name and try again"]
                }), 404
            
            data = request.json
            assignments = data.get("assignments", {})  # {position_index: player_name}
            
            if not assignments:
                return jsonify({
                    "success": False,
                    "error": "No player assignments provided",
                    "suggestions": ["Select players for at least one position"]
                }), 400
            
            # Convert and validate assignments
            player_assignments = {}
            validation_errors = []
            
            for pos_str, player_name in assignments.items():
                try:
                    pos_idx = int(pos_str)
                    
                    # Skip empty assignments
                    if not player_name or not player_name.strip():
                        continue
                        
                    player_name = player_name.strip()
                    
                    # Validate position index
                    if not (0 <= pos_idx < len(formation.positions)):
                        validation_errors.append(f"Invalid position index: {pos_idx}")
                        continue
                    
                    # Validate player exists in roster
                    if player_name not in app_state.game_state.roster:
                        validation_errors.append(f"Player '{player_name}' not found in roster")
                        continue
                    
                    player = app_state.game_state.roster[player_name]
                    player_assignments[pos_idx] = player_name
                    
                    # Validate individual assignment
                    assignment_result = app_state.formation_validator.validate_player_assignment(
                        formation, pos_idx, player_name, player.number
                    )
                    
                    if not assignment_result.is_valid:
                        validation_errors.extend(assignment_result.errors)
                    
                except ValueError:
                    validation_errors.append(f"Invalid position index format: {pos_str}")
                    continue
            
            # Check for duplicate player assignments
            assigned_players = list(player_assignments.values())
            if len(assigned_players) != len(set(assigned_players)):
                validation_errors.append("Cannot assign the same player to multiple positions")
            
            # Return validation errors if any
            if validation_errors:
                error_result = app_state.lineup_edge_handler.handle_player_assignment_error(
                    type('ValidationResult', (), {'is_valid': False, 'errors': validation_errors})()
                )
                return jsonify(error_result), 400
            
            # Perform the assignment
            try:
                updated_formation = app_state.strategy_service.assign_players_to_formation(
                    formation, player_assignments
                )
                
                # Get completeness information
                assigned, total, missing_types = app_state.formation_validator.get_formation_completeness(updated_formation)
                
                response = {
                    "success": True,
                    "formation": updated_formation.to_dict(),
                    "completeness": {
                        "assigned": assigned,
                        "total": total,
                        "percentage": round((assigned / total) * 100, 1),
                        "missing_types": missing_types
                    }
                }
                
                # Add warnings for incomplete lineup
                if assigned < total:
                    response["warnings"] = [
                        f"Lineup is {assigned}/{total} complete",
                        f"Missing positions: {', '.join(missing_types) if missing_types else 'Various'}"
                    ]
                
                if missing_types:
                    response["warnings"] = response.get("warnings", []) + [
                        f"Critical positions missing: {', '.join(missing_types)}"
                    ]
                
                return jsonify(response)
                
            except Exception as assignment_error:
                return jsonify({
                    "success": False,
                    "error": f"Failed to assign players: {str(assignment_error)}",
                    "suggestions": [
                        "Check that all selected players are available",
                        "Ensure no player conflicts exist",
                        "Try refreshing and attempting the assignment again"
                    ]
                }), 500
            
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": f"Unexpected error during player assignment: {str(e)}",
                "suggestions": ["Please try again or contact support if the problem persists"]
            }), 500

    @app.route("/api/formations/<formation_name>/validate", methods=["GET"])
    def validate_formation_for_game(formation_name):
        """Validate formation readiness for starting a game."""
        try:
            formation = app_state.strategy_service.get_formation(formation_name)
            if not formation:
                return jsonify({
                    "success": False, 
                    "error": "Formation not found",
                    "can_start_game": False
                }), 404
            
            # Comprehensive validation for game start
            validation_result = app_state.formation_validator.validate_formation(
                formation, 
                is_update=False,
                is_game_active=app_state.game_state.is_active()
            )
            
            # Get completeness information
            assigned, total, missing_types = app_state.formation_validator.get_formation_completeness(formation)
            
            # Determine if game can start
            can_start_game = (
                validation_result.is_valid and 
                assigned == total and 
                len(missing_types) == 0 and
                not app_state.game_state.is_active()
            )
            
            response = {
                "success": True,
                "formation_name": formation_name,
                "is_valid": validation_result.is_valid,
                "can_start_game": can_start_game,
                "completeness": {
                    "assigned": assigned,
                    "total": total,
                    "percentage": round((assigned / total) * 100, 1),
                    "missing_types": missing_types
                },
                "validation_errors": validation_result.errors,
                "warnings": [],
                "requirements": {
                    "needs_full_lineup": assigned < total,
                    "needs_goalkeeper": "Goalkeeper" in missing_types,
                    "needs_outfield_players": len(missing_types) > 1 or (len(missing_types) == 1 and "Goalkeeper" not in missing_types),
                    "game_already_active": app_state.game_state.is_active()
                }
            }
            
            # Add specific warnings and suggestions
            if assigned < total:
                response["warnings"].append(f"Lineup incomplete: {assigned}/{total} positions filled")
            
            if missing_types:
                response["warnings"].append(f"Missing critical positions: {', '.join(missing_types)}")
            
            if app_state.game_state.is_active():
                response["warnings"].append("Game is already in progress")
            
            if not validation_result.is_valid:
                response["warnings"].extend(validation_result.errors)
            
            # Add suggestions for fixing issues
            if not can_start_game:
                suggestions = []
                if assigned < total:
                    suggestions.append(f"Assign players to all {app_state.game_state.field_size} positions")
                if "Goalkeeper" in missing_types:
                    suggestions.append("Assign a goalkeeper")
                if len(missing_types) > 1:
                    suggestions.append("Fill all critical position types")
                if app_state.game_state.is_active():
                    suggestions.append("End current game before starting new one")
                    
                response["suggestions"] = suggestions
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": f"Validation failed: {str(e)}",
                "can_start_game": False
            }), 500

    @app.route("/api/formations/<formation_name>/suggestions", methods=["GET"])
    def get_rotation_suggestions(formation_name):
        """Get position rotation suggestions for a formation."""
        try:
            formation = app_state.strategy_service.get_formation(formation_name)
            if not formation:
                return jsonify({"success": False, "error": "Formation not found"}), 404
            
            available_players = list(app_state.game_state.roster.values())
            suggestions = app_state.strategy_service.suggest_position_rotations(formation, available_players)
            
            return jsonify({
                "success": True,
                "suggestions": [
                    {
                        "out_player": out_player,
                        "in_player": in_player,
                        "position": position.value
                    }
                    for out_player, in_player, position in suggestions
                ]
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/strategy/substitution-plans", methods=["GET"])
    def get_substitution_plans():
        """Get all substitution plans."""
        try:
            plans = app_state.strategy_service.list_substitution_plans()
            return jsonify({
                "success": True,
                "plans": [plan.to_dict() for plan in plans]
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/strategy/substitution-plans", methods=["POST"])
    def create_substitution_plan():
        """Create a substitution plan."""
        try:
            data = request.json
            
            name = data.get("name", "").strip()
            if not name:
                return jsonify({"success": False, "error": "Plan name is required"}), 400
            
            # Parse substitutions: [(out_player, in_player, minute)]
            substitutions = []
            for sub_data in data.get("substitutions", []):
                substitutions.append((
                    sub_data.get("out_player", ""),
                    sub_data.get("in_player", ""),
                    sub_data.get("minute", 0)
                ))
            
            plan = app_state.strategy_service.create_substitution_plan(name, substitutions)
            
            return jsonify({
                "success": True,
                "plan": plan.to_dict()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/strategy/opponent-notes", methods=["GET"])
    def get_opponent_notes():
        """Get all opponent notes."""
        try:
            notes = app_state.strategy_service.list_opponent_notes()
            return jsonify({
                "success": True,
                "notes": [note.to_dict() for note in notes]
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/strategy/opponent-notes", methods=["POST"])
    def create_opponent_notes():
        """Create opponent scouting notes."""
        try:
            data = request.json
            
            opponent_name = data.get("opponent_name", "").strip()
            if not opponent_name:
                return jsonify({"success": False, "error": "Opponent name is required"}), 400
            
            notes = app_state.strategy_service.create_opponent_notes(opponent_name)
            
            # Update with provided data
            update_data = {k: v for k, v in data.items() if k != "opponent_name"}
            if update_data:
                notes = app_state.strategy_service.update_opponent_notes(opponent_name, **update_data)
            
            return jsonify({
                "success": True,
                "notes": notes.to_dict() if notes else None
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return app


def run_web_app(host: str = "127.0.0.1", port: int = 7122, static_folder: str = ".") -> None:
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