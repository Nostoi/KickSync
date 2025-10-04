"""
Test script to verify the game start fix.

This script tests that:
1. GameState initializes with proper timer lists
2. StartGameCommand can execute successfully
3. The web app properly initializes game state
"""
from src.models.game_state import GameState
from src.models.player import Player
from src.services.game_commands import StartGameCommand, GameCommandManager

def test_game_state_initialization():
    """Test that a fresh GameState can be initialized properly."""
    print("Testing GameState initialization...")
    
    game_state = GameState()
    print(f"  Initial period_elapsed: {game_state.period_elapsed}")
    print(f"  Initial period_count: {game_state.period_count}")
    
    # Ensure timer lists
    game_state.ensure_timer_lists()
    print(f"  After ensure_timer_lists(): {game_state.period_elapsed}")
    
    assert len(game_state.period_elapsed) == game_state.period_count, \
        f"Expected {game_state.period_count} periods, got {len(game_state.period_elapsed)}"
    assert len(game_state.period_adjustments) == game_state.period_count
    assert len(game_state.period_stoppage) == game_state.period_count
    
    print("  ✅ GameState initialization successful\n")


def test_start_game_command():
    """Test that StartGameCommand executes without errors."""
    print("Testing StartGameCommand execution...")
    
    game_state = GameState()
    game_state.ensure_timer_lists()
    
    # Add some players to roster
    game_state.roster["Player 1"] = Player(name="Player 1", number=1)
    game_state.roster["Player 2"] = Player(name="Player 2", number=2)
    
    # Create and execute command
    command = StartGameCommand(game_state)
    success = command.execute()
    
    assert success, "StartGameCommand.execute() should return True"
    assert game_state.game_start_ts is not None, "game_start_ts should be set"
    assert game_state.period_start_ts is not None, "period_start_ts should be set"
    assert not game_state.paused, "Game should not be paused after start"
    
    print(f"  Game started at: {game_state.game_start_ts}")
    print(f"  Period started at: {game_state.period_start_ts}")
    print(f"  Paused: {game_state.paused}")
    print("  ✅ StartGameCommand execution successful\n")


def test_web_app_state_initialization():
    """Test that WebAppState initializes properly."""
    print("Testing WebAppState initialization...")
    
    from src.ui.web_app import WebAppState
    
    app_state = WebAppState()
    
    # Check that game state is initialized
    assert app_state.game_state is not None
    assert len(app_state.game_state.period_elapsed) == app_state.game_state.period_count, \
        "Timer lists should be initialized"
    
    print(f"  Timer lists initialized: {app_state.game_state.period_elapsed}")
    print("  ✅ WebAppState initialization successful\n")


def test_full_game_start_flow():
    """Test the full flow of starting a game from web app state."""
    print("Testing full game start flow...")
    
    from src.ui.web_app import WebAppState
    
    app_state = WebAppState()
    
    # Add players
    app_state.game_state.roster["Goalkeeper"] = Player(name="Goalkeeper", number=1, position="goalkeeper")
    for i in range(2, 12):
        app_state.game_state.roster[f"Player {i}"] = Player(name=f"Player {i}", number=i)
    
    print(f"  Added {len(app_state.game_state.roster)} players to roster")
    
    # Execute start game command
    command_manager = GameCommandManager()
    command = StartGameCommand(app_state.game_state)
    
    success = command_manager.execute_command(command)
    
    assert success, "Command execution should succeed"
    assert app_state.game_state.is_active(), "Game should be active"
    
    print(f"  Game is active: {app_state.game_state.is_active()}")
    print("  ✅ Full game start flow successful\n")


if __name__ == "__main__":
    print("="*60)
    print("GAME START FIX VERIFICATION")
    print("="*60 + "\n")
    
    try:
        test_game_state_initialization()
        test_start_game_command()
        test_web_app_state_initialization()
        test_full_game_start_flow()
        
        print("="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe fix successfully resolves the game start issue.")
        print("Users can now start games without the 'Failed to start game timer' error.")
        
    except Exception as e:
        print("="*60)
        print("❌ TEST FAILED!")
        print("="*60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
