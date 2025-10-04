#!/usr/bin/env python3
"""
Test script to validate the lineup visual cues are working.
"""
import re

def test_visual_cues():
    """Test that the visual cue CSS and JavaScript changes are present."""
    with open('/Users/markjedrzejczyk/dev/projects/soccer_coach/index.html', 'r') as f:
        content = f.read()
    
    print("Testing lineup visual cues implementation...")
    
    # Test 1: Check CSS classes are defined
    css_tests = [
        '.slot-filled',
        '.player-used', 
        'rgba(36, 200, 139, 0.15)',  # Green for filled slots
        'rgba(255, 107, 107, 0.15)',  # Red for used players
        'content: \' ✓\';',  # Checkmark for filled slots
        'content: \' ASSIGNED\';'  # Label for used players
    ]
    
    for test in css_tests:
        if test in content:
            print(f"✅ Found CSS: {test}")
        else:
            print(f"❌ Missing CSS: {test}")
    
    # Test 2: Check JavaScript functions are updated
    js_tests = [
        'assignedSlots.has(i)',  # highlightSlots checks for filled slots
        'li.classList.add(\'slot-filled\')',  # Adds filled class
        'assignedPlayers.has(p.name)',  # renderLineup checks used players
        'tr.classList.add(\'player-used\')',  # Adds used class
        'renderLineup(); // Refresh visual cues'  # Refreshes after changes
    ]
    
    for test in js_tests:
        if test in content:
            print(f"✅ Found JS: {test}")
        else:
            print(f"❌ Missing JS: {test}")
    
    print("\nVisual cues implementation validation complete!")

if __name__ == "__main__":
    test_visual_cues()