#!/usr/bin/env python3
"""
Test script to validate the lineup assignment fixes.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
JS_PATH = REPO_ROOT / "frontend" / "src" / "app.js"


def test_assignment_fixes():
    """Test that the assignment fixes are implemented correctly."""
    content = JS_PATH.read_text(encoding="utf-8")

    print("Testing assignment persistence fixes...")

    # Test 1: Check that assignment table is no longer cleared in renderLineup
    if 'ui.assignTable.innerHTML = "";' in content.split('function renderLineup()')[1].split('function highlightSlots()')[0]:
        print("❌ renderLineup() still clears assignment table")
    else:
        print("✅ renderLineup() no longer clears assignment table")

    # Test 2: Check that updateRosterVisualCues function exists
    if 'function updateRosterVisualCues()' in content:
        print("✅ updateRosterVisualCues() function created")
    else:
        print("❌ updateRosterVisualCues() function missing")

    # Test 3: Check that assignSelectedSlot calls the right functions
    if 'highlightSlots();\n  \n  // Update player visual cues by re-rendering just the roster table\n  updateRosterVisualCues();' in content:
        print("✅ assignSelectedSlot() uses targeted refresh functions")
    else:
        print("❌ assignSelectedSlot() not using targeted refresh")

    # Test 4: Check that clear button uses targeted functions
    if 'highlightSlots(); // Refresh slot visual cues\n  updateRosterVisualCues(); // Refresh player visual cues' in content:
        print("✅ Clear button uses targeted refresh functions")
    else:
        print("❌ Clear button not using targeted refresh")

    # Test 5: Check that slot highlighting logic is improved
    if 'if (i === selectedSlotIndex) {\n      li.style.background = "#0c1732";\n    } else if (!assignedSlots.has(i)) {\n      li.style.background = "transparent";\n    }' in content:
        print("✅ Slot highlighting preserves filled state")
    else:
        print("❌ Slot highlighting logic needs improvement")

    print("\nAssignment fixes validation complete!")


if __name__ == "__main__":
    test_assignment_fixes()
