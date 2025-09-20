#!/usr/bin/env python3
"""
Test script to verify the new modular structure works correctly.

This script tests basic functionality of the refactored application.
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        print("Testing imports...")
        
        # Test models
        from src.models import Player, GameState
        print("✓ Models imported successfully")
        
        # Test services
        from src.services import PersistenceService, TimerService
        print("✓ Services imported successfully")
        
        # Test utilities
        from src.utils import fmt_mmss, now_ts, APP_TITLE
        print("✓ Utilities imported successfully")
        
        # Test UI modules
        from src.ui import create_tkinter_app, create_app
        print("✓ UI modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of core classes."""
    try:
        print("\nTesting basic functionality...")
        
        # Test Player creation
        from src.models import Player
        player = Player(name="Test Player", number="1", preferred="ST,MF")
        assert player.name == "Test Player"
        assert player.preferred_list() == ["ST", "MF"]
        print("✓ Player model works correctly")
        
        # Test GameState creation
        from src.models import GameState
        game_state = GameState()
        game_state.roster[player.name] = player
        assert len(game_state.roster) == 1
        print("✓ GameState model works correctly")
        
        # Test TimerService
        from src.services import TimerService
        timer_service = TimerService(game_state)
        initial_elapsed = timer_service.get_game_elapsed_seconds()
        assert initial_elapsed == 0  # Game not started
        print("✓ TimerService works correctly")
        
        # Test time formatting
        from src.utils import fmt_mmss
        assert fmt_mmss(90) == "01:30"
        assert fmt_mmss(3661) == "61:01"
        print("✓ Time formatting works correctly")
        
        # Test Flask app creation
        from src.ui.web_app import create_app
        app = create_app()
        assert app is not None
        print("✓ Flask app creation works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

def test_persistence():
    """Test data persistence functionality."""
    try:
        print("\nTesting persistence...")
        
        from src.models import Player, GameState
        from src.services import PersistenceService
        import tempfile
        import json
        
        # Create test data
        game_state = GameState()
        player1 = Player(name="Alice", number="1", preferred="GK")
        player2 = Player(name="Bob", number="2", preferred="DF,MF")
        game_state.roster["Alice"] = player1
        game_state.roster["Bob"] = player2
        
        # Test saving
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_file = f.name
        
        PersistenceService.save_game_to_file(game_state, test_file)
        print("✓ Game state saved successfully")
        
        # Test loading
        loaded_state = PersistenceService.load_game_from_file(test_file)
        assert len(loaded_state.roster) == 2
        assert "Alice" in loaded_state.roster
        assert "Bob" in loaded_state.roster
        print("✓ Game state loaded successfully")
        
        # Cleanup
        os.unlink(test_file)
        
        return True
        
    except Exception as e:
        print(f"✗ Persistence test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Soccer Coach Sideline Timekeeper - Structure Verification")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_basic_functionality()
    all_passed &= test_persistence()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! New structure is working correctly.")
        print("\nYou can now run:")
        print("  - Desktop app: python run_desktop.py")
        print("  - Web app: python run_web.py")
        print("  - Legacy desktop: python coach_timer.py")
        print("  - Legacy web: python app.py")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())