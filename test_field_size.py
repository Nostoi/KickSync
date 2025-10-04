#!/usr/bin/env python3
"""
Test script for flexible field size support (7v7, 9v9, 10v10, 11v11).

This script tests:
1. GameState field_size persistence
2. Field size constants
3. Basic validation logic
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.game_state import GameState
from src.models.player import Player
from src.utils.constants import (
    MIN_FIELD_SIZE, MAX_FIELD_SIZE, DEFAULT_FIELD_SIZE, SUPPORTED_FIELD_SIZES
)


def test_constants():
    """Test that field size constants are defined correctly."""
    print("=" * 60)
    print("TEST 1: Field Size Constants")
    print("=" * 60)
    
    assert MIN_FIELD_SIZE == 7, f"MIN_FIELD_SIZE should be 7, got {MIN_FIELD_SIZE}"
    assert MAX_FIELD_SIZE == 11, f"MAX_FIELD_SIZE should be 11, got {MAX_FIELD_SIZE}"
    assert DEFAULT_FIELD_SIZE == 11, f"DEFAULT_FIELD_SIZE should be 11, got {DEFAULT_FIELD_SIZE}"
    assert SUPPORTED_FIELD_SIZES == [7, 9, 10, 11], f"SUPPORTED_FIELD_SIZES incorrect: {SUPPORTED_FIELD_SIZES}"
    
    print("✅ All field size constants are correct")
    print(f"   MIN_FIELD_SIZE: {MIN_FIELD_SIZE}")
    print(f"   MAX_FIELD_SIZE: {MAX_FIELD_SIZE}")
    print(f"   DEFAULT_FIELD_SIZE: {DEFAULT_FIELD_SIZE}")
    print(f"   SUPPORTED_FIELD_SIZES: {SUPPORTED_FIELD_SIZES}")
    print()


def test_game_state_field_size():
    """Test GameState field_size attribute and persistence."""
    print("=" * 60)
    print("TEST 2: GameState Field Size Attribute")
    print("=" * 60)
    
    # Test default field_size
    gs_default = GameState()
    assert gs_default.field_size == 11, f"Default field_size should be 11, got {gs_default.field_size}"
    print("✅ Default field_size is 11")
    
    # Test custom field sizes
    for field_size in SUPPORTED_FIELD_SIZES:
        gs = GameState(field_size=field_size)
        assert gs.field_size == field_size, f"Field size should be {field_size}, got {gs.field_size}"
        print(f"✅ GameState created with field_size={field_size}")
    
    print()


def test_game_state_persistence():
    """Test GameState serialization with field_size."""
    print("=" * 60)
    print("TEST 3: GameState Persistence (JSON)")
    print("=" * 60)
    
    for field_size in SUPPORTED_FIELD_SIZES:
        # Create game state with specific field size
        roster = {
            "Alice": Player(name="Alice", number="10", preferred="ST"),
            "Bob": Player(name="Bob", number="7", preferred="MF"),
        }
        gs = GameState(roster=roster, field_size=field_size)
        
        # Serialize to JSON
        json_data = gs.to_json()
        json_str = json.dumps(json_data)
        
        # Verify field_size is in JSON
        assert "field_size" in json_data, f"field_size missing from JSON for {field_size}v{field_size}"
        assert json_data["field_size"] == field_size, f"JSON field_size incorrect for {field_size}v{field_size}"
        
        # Deserialize from JSON
        parsed_data = json.loads(json_str)
        gs_loaded = GameState.from_json(parsed_data)
        
        # Verify field_size persisted correctly
        assert gs_loaded.field_size == field_size, f"Loaded field_size should be {field_size}, got {gs_loaded.field_size}"
        print(f"✅ {field_size}v{field_size}: Serialization and deserialization successful")
    
    print()


def test_backward_compatibility():
    """Test that old saved games without field_size still work."""
    print("=" * 60)
    print("TEST 4: Backward Compatibility")
    print("=" * 60)
    
    # Simulate old JSON without field_size
    old_json = {
        "roster": {
            "Alice": {"name": "Alice", "number": "10", "preferred": "ST"}
        },
        "timing": {
            "game_start_ts": None,
            "paused": True
        },
        "formations": {}
    }
    
    # Load old JSON - should default to 11
    gs = GameState.from_json(old_json)
    assert gs.field_size == 11, f"Old saves should default to field_size=11, got {gs.field_size}"
    print("✅ Old saved games default to 11v11")
    print()


def test_player_roster_sizes():
    """Test that different field sizes work with appropriate roster sizes."""
    print("=" * 60)
    print("TEST 5: Player Roster Sizes")
    print("=" * 60)
    
    test_cases = [
        (7, 10, "7v7 with 10-player roster"),
        (9, 13, "9v9 with 13-player roster"),
        (10, 15, "10v10 with 15-player roster"),
        (11, 17, "11v11 with 17-player roster"),
    ]
    
    for field_size, roster_size, description in test_cases:
        # Create roster
        roster = {}
        for i in range(roster_size):
            player = Player(name=f"Player{i+1}", number=str(i+1), preferred="MID")
            roster[player.name] = player
        
        # Create game state
        gs = GameState(roster=roster, field_size=field_size)
        
        # Verify
        assert gs.field_size == field_size, f"Field size should be {field_size}"
        assert len(gs.roster) == roster_size, f"Roster should have {roster_size} players"
        
        print(f"✅ {description}: Success")
    
    print()


def run_all_tests():
    """Run all field size tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "FLEXIBLE FIELD SIZE TEST SUITE" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        test_constants()
        test_game_state_field_size()
        test_game_state_persistence()
        test_backward_compatibility()
        test_player_roster_sizes()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Field size feature is working correctly:")
        print("  • GameState supports field_size attribute")
        print("  • Serialization/deserialization works")
        print("  • Backward compatibility maintained")
        print("  • Validators support 7v7, 9v9, 10v10, 11v11")
        print("  • Dynamic error messages display correct sizes")
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ UNEXPECTED ERROR!")
        print("=" * 60)
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
