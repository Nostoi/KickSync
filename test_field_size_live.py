#!/usr/bin/env python3
"""
Live integration test for field size feature using requests.
Tests the web API directly.
"""

import sys
import time
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

BASE_URL = "http://127.0.0.1:7122"


def wait_for_server(timeout=10):
    """Wait for server to be ready."""
    print("⏳ Waiting for server to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{BASE_URL}/", timeout=1)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    print("❌ Server did not start in time")
    return False


def test_load_roster_with_field_size(field_size, num_players):
    """Test loading a roster with a specific field size."""
    print(f"\n{'='*60}")
    print(f"TEST: Loading roster with {field_size}v{field_size} format ({num_players} players)")
    print(f"{'='*60}")
    
    # Create test roster
    players = []
    for i in range(num_players):
        players.append({
            "name": f"Player{i+1}",
            "number": str(i+1),
            "preferred": "MID"
        })
    
    # Send request with field_size
    try:
        response = requests.post(
            f"{BASE_URL}/api/roster",
            json={
                "players": players,
                "field_size": field_size
            },
            timeout=5
        )
        
        print(f"Response Status: {response.status_code}")
        result = response.json()
        
        if response.status_code == 200 and result.get("success"):
            print(f"✅ SUCCESS: Roster loaded with {field_size}v{field_size} format")
            print(f"   Players: {len(players)}")
            print(f"   Message: {result.get('message', 'N/A')}")
            return True
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_game_state_persistence():
    """Test that field_size persists in game state."""
    print(f"\n{'='*60}")
    print(f"TEST: Field size persistence in game state")
    print(f"{'='*60}")
    
    try:
        # Get current game state
        response = requests.get(f"{BASE_URL}/api/state", timeout=5)
        
        if response.status_code == 200:
            state = response.json()
            game_state = state.get("game_state", {})
            field_size = game_state.get("field_size", None)
            
            if field_size is not None:
                print(f"✅ SUCCESS: field_size found in game state")
                print(f"   Current field_size: {field_size}")
                return True
            else:
                print(f"❌ FAILED: field_size not in game_state")
                print(f"   State keys: {list(state.keys())}")
                print(f"   Game state keys: {list(game_state.keys())}")
                return False
        else:
            print(f"❌ FAILED: Could not get game state (status {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_formation_validation_with_field_size():
    """Test that formation validation uses field_size."""
    print(f"\n{'='*60}")
    print(f"TEST: Formation validation with different field sizes")
    print(f"{'='*60}")
    
    # First load a 9v9 roster
    print("\n1. Loading 9v9 roster...")
    players = [{"name": f"Player{i}", "number": str(i), "preferred": "MID"} for i in range(13)]
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/roster",
            json={"players": players, "field_size": 9},
            timeout=5
        )
        
        if not response.json().get("success"):
            print("❌ Failed to load roster")
            return False
        
        print("✅ 9v9 roster loaded")
        
        # Try to create an 11-position formation (should fail for 9v9)
        print("\n2. Creating 11-position formation (should fail for 9v9)...")
        
        positions = []
        # Add goalkeeper
        positions.append({"x": 50, "y": 10, "position_code": "GK"})
        # Add 10 more positions (total 11)
        for i in range(10):
            positions.append({"x": 50, "y": 30 + i*5, "position_code": "MID"})
        
        response = requests.post(
            f"{BASE_URL}/api/formations",
            json={
                "name": "Test 11-position",
                "formation_type": "4-4-2",
                "positions": positions
            },
            timeout=5
        )
        
        result = response.json()
        
        if not result.get("success"):
            print("✅ SUCCESS: 11-position formation correctly rejected for 9v9")
            print(f"   Error: {result.get('errors', ['N/A'])[0]}")
            
            # Check if error message mentions "9 positions"
            errors = str(result.get('errors', []))
            if "9" in errors:
                print("✅ Error message correctly mentions 9 positions")
                return True
            else:
                print("⚠️  Warning: Error message doesn't mention correct field size")
                return True
        else:
            print("❌ FAILED: 11-position formation was accepted for 9v9")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_live_tests():
    """Run all live integration tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "FIELD SIZE LIVE INTEGRATION TESTS" + " " * 17 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Wait for server
    if not wait_for_server():
        print("\n❌ Server not available. Please start with: python run_web.py")
        return 1
    
    results = []
    
    # Test 1: 7v7 with 10 players
    results.append(test_load_roster_with_field_size(7, 10))
    
    # Test 2: 9v9 with 13 players
    results.append(test_load_roster_with_field_size(9, 13))
    
    # Test 3: 10v10 with 15 players
    results.append(test_load_roster_with_field_size(10, 15))
    
    # Test 4: 11v11 with 17 players
    results.append(test_load_roster_with_field_size(11, 17))
    
    # Test 5: Field size persistence
    results.append(test_game_state_persistence())
    
    # Test 6: Formation validation
    results.append(test_formation_validation_with_field_size())
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED! ({passed}/{total})")
        print("=" * 60)
        print("\n🎉 Field size feature is working correctly in live server!")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED: {passed}/{total} passed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(run_live_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
