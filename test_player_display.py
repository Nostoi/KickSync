#!/usr/bin/env python3
"""Test script to verify player numbers are being returned by the API."""

import requests
import json

def test_players_api():
    """Test that the /api/players endpoint returns player numbers."""
    
    # First, load some test players via the roster endpoint
    print("=" * 60)
    print("Testing Player Number Display")
    print("=" * 60)
    
    test_roster = [
        {"name": "Evan", "number": "08", "preferred": "ST"},
        {"name": "Silas", "number": "04", "preferred": "ST"},
        {"name": "Ivan", "number": "16", "preferred": "ST"},
    ]
    
    # Load roster
    print("\n1. Loading test roster...")
    response = requests.post(
        'http://127.0.0.1:7122/api/roster',
        json={"players": test_roster}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Roster loaded: {result.get('message', 'Success')}")
    else:
        print(f"   ✗ Failed to load roster: {response.status_code}")
        return False
    
    # Get players
    print("\n2. Fetching players from /api/players...")
    response = requests.get('http://127.0.0.1:7122/api/players')
    
    if response.status_code != 200:
        print(f"   ✗ Failed to fetch players: {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get('success'):
        print(f"   ✗ API returned success=False")
        return False
    
    players = data.get('players', [])
    print(f"   ✓ Found {len(players)} players")
    
    # Check if numbers are present
    print("\n3. Checking player numbers...")
    all_have_numbers = True
    for player in players[:3]:  # Check first 3
        name = player.get('name', 'Unknown')
        number = player.get('number', 'MISSING')
        preferred = player.get('preferred', 'N/A')
        
        has_number = number and number != 'MISSING'
        status = "✓" if has_number else "✗"
        
        print(f"   {status} {name}: #{number} - {preferred}")
        
        if not has_number:
            all_have_numbers = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_have_numbers:
        print("✓ SUCCESS: All players have their numbers!")
        print("\nThe 'Players' tab should now display numbers correctly.")
    else:
        print("✗ FAILURE: Some players are missing numbers")
        print("\nDebugging info:")
        print(json.dumps(players[0] if players else {}, indent=2))
    print("=" * 60)
    
    return all_have_numbers

if __name__ == "__main__":
    try:
        success = test_players_api()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to server at http://127.0.0.1:7122")
        print("   Make sure the web app is running: python run_web.py")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        exit(1)
