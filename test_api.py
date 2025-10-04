#!/usr/bin/env python3
"""
Test script to verify the API functionality.
"""
import requests
import json

def test_roster_sync():
    """Test the roster synchronization workflow."""
    base_url = "http://127.0.0.1:8123"
    
    # Test data - same format that the web UI would send
    test_roster = {
        "players": [
            {"name": "Test Player 1", "number": "1", "preferred": "GK"},
            {"name": "Test Player 2", "number": "2", "preferred": "CB"},
            {"name": "Test Player 3", "number": "3", "preferred": "LB"},
            {"name": "Test Player 4", "number": "4", "preferred": "RB"},
            {"name": "Test Player 5", "number": "5", "preferred": "CM"},
            {"name": "Test Player 6", "number": "6", "preferred": "CAM"},
            {"name": "Test Player 7", "number": "7", "preferred": "LW"},
            {"name": "Test Player 8", "number": "8", "preferred": "RW"},
            {"name": "Test Player 9", "number": "9", "preferred": "ST"},
            {"name": "Test Player 10", "number": "10", "preferred": "ST"}
        ]
    }
    
    print("Testing roster sync workflow...")
    
    # Step 1: Clear and set roster
    print("1. Setting roster...")
    response = requests.post(f"{base_url}/api/roster", json=test_roster)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Step 2: Get players
    print("\n2. Getting players...")
    response = requests.get(f"{base_url}/api/players")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data.get('success')}")
        print(f"   Player count: {data.get('count')}")
        if data.get('players'):
            print(f"   First player: {data['players'][0]['name']}")
    else:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    test_roster_sync()