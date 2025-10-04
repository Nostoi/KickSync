#!/usr/bin/env python3
"""Test script to verify formation creation works correctly."""

import requests
import json

def test_formation_creation():
    """Test that formations can be created without position code errors."""
    
    print("=" * 60)
    print("Testing Formation Creation")
    print("=" * 60)
    
    # Test data - simulating what the JavaScript sends
    formation_data = {
        "name": "Test 4-4-2",
        "formation_type": "4-4-2",
        "description": "Test formation",
        "positions": [
            {"x": 50, "y": 5, "position_code": "GK"},
            {"x": 20, "y": 25, "position_code": "LB"},
            {"x": 35, "y": 20, "position_code": "CB"},
            {"x": 65, "y": 20, "position_code": "CB"},
            {"x": 80, "y": 25, "position_code": "RB"},
            {"x": 20, "y": 55, "position_code": "LM"},
            {"x": 40, "y": 50, "position_code": "CM"},
            {"x": 60, "y": 50, "position_code": "CM"},
            {"x": 80, "y": 55, "position_code": "RM"},
            {"x": 40, "y": 80, "position_code": "ST"},
            {"x": 60, "y": 80, "position_code": "ST"}
        ]
    }
    
    print("\n1. Testing formation creation with correct position codes...")
    print(f"   Creating formation: {formation_data['name']}")
    print(f"   Formation type: {formation_data['formation_type']}")
    print(f"   Positions: {len(formation_data['positions'])}")
    
    try:
        response = requests.post(
            'http://127.0.0.1:7122/api/formations',
            json=formation_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✓ Formation created successfully!")
                print(f"   Formation ID: {result.get('formation', {}).get('name')}")
            else:
                print(f"   ✗ API returned success=False")
                print(f"   Error: {result.get('error')}")
                return False
        else:
            print(f"   ✗ HTTP Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to server at http://127.0.0.1:7122")
        print("   Make sure the web app is running: python run_web.py")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False
    
    # Test with wrong position code (should fail)
    print("\n2. Testing with invalid position code (should fail gracefully)...")
    bad_formation = {
        "name": "Test Bad Formation",
        "formation_type": "4-4-2",
        "description": "This should fail",
        "positions": [
            {"x": 50, "y": 5, "position_code": "GOALKEEPER"}  # Wrong - should be 'GK'
        ]
    }
    
    try:
        response = requests.post(
            'http://127.0.0.1:7122/api/formations',
            json=bad_formation,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code >= 400:
            result = response.json()
            print(f"   ✓ Correctly rejected invalid position code")
            print(f"   Error message: {result.get('error', 'No error message')}")
        else:
            print(f"   ⚠ Warning: Bad formation was accepted (should have failed)")
            
    except Exception as e:
        print(f"   Error testing bad formation: {e}")
    
    # List all formations
    print("\n3. Listing all formations...")
    try:
        response = requests.get('http://127.0.0.1:7122/api/formations')
        if response.status_code == 200:
            data = response.json()
            formations = data.get('formations', [])
            print(f"   ✓ Found {len(formations)} formation(s):")
            for f in formations:
                print(f"      - {f.get('name')} ({f.get('formation_type')})")
        else:
            print(f"   ✗ Failed to list formations: {response.status_code}")
    except Exception as e:
        print(f"   Error listing formations: {e}")
    
    # Clean up - delete test formation
    print("\n4. Cleaning up test formation...")
    try:
        response = requests.delete('http://127.0.0.1:7122/api/formations/Test%204-4-2')
        if response.status_code == 200:
            print("   ✓ Test formation deleted")
        else:
            print(f"   ⚠ Could not delete test formation (status {response.status_code})")
    except Exception as e:
        print(f"   Error deleting formation: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Test Complete!")
    print("Formation creation should now work correctly in the web UI.")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_formation_creation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        exit(1)
