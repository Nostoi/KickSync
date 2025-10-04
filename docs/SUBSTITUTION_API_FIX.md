# Substitution API Fix

## Problem

The `/api/substitution` endpoint in `src/ui/web_app.py` was calling non-existent methods on the `Player` model:
- `out_player.sub_off(current_time)` - method doesn't exist
- `in_player.sub_on(current_time, out_player.position)` - method doesn't exist

This would cause the API endpoint to fail with an `AttributeError` when trying to make substitutions programmatically.

## Solution

Fixed the API endpoint to use the correct methods from the `Player` model:

### Before (Broken Code):
```python
# Perform substitution
current_time = now_ts()
out_player.sub_off(current_time)
in_player.sub_on(current_time, out_player.position)
```

### After (Fixed Code):
```python
# Perform substitution
current_time = now_ts()

# Save the position before ending the stint
position_to_fill = out_player.position

# End the outgoing player's stint
out_player.end_stint(current_time)

# Start the incoming player's stint in the vacated position
in_player.position = position_to_fill
in_player.start_stint(current_time)
```

## What the Fix Does

1. **Saves the position** before ending the outgoing player's stint (since `end_stint()` clears the position)
2. **Uses `end_stint()`** which:
   - Adds current stint time to the player's total playing time
   - Sets `on_field = False`
   - Clears the `position`
   - Resets `stint_start_ts = None`

3. **Uses `start_stint()`** which:
   - Sets `on_field = True`
   - Records the `stint_start_ts`
   
4. **Manually assigns the position** to the incoming player before starting their stint

## Impact

### Before Fix:
- ❌ API endpoint would crash with `AttributeError`
- ❌ Could not make substitutions via API calls
- ✅ Frontend queue system still worked (it has its own implementation)

### After Fix:
- ✅ API endpoint works correctly
- ✅ Can make substitutions programmatically via API
- ✅ Frontend queue system continues to work
- ✅ Consistent behavior between frontend and backend

## Testing

Created `test_substitution_api.py` which verifies:
1. ✅ Basic substitution logic with Player methods
2. ✅ Web app substitution endpoint simulation
3. ✅ Multiple sequential substitutions
4. ✅ Players returning to field after being substituted off

All tests pass successfully.

## Usage

### Via API (Now Fixed):
```python
POST /api/substitution
{
  "out_name": "Player A",
  "in_name": "Player B"
}
```

### Via Frontend Queue System (Always Worked):
1. Click player in "On Field" table (selects OUT player)
2. Click player in "Roster" table (selects IN player)
3. Click "Queue Selected"
4. Click "Commit Subs" to execute all queued substitutions

## Files Modified

1. `src/ui/web_app.py` - Fixed the `/api/substitution` endpoint
2. `test_substitution_api.py` - Comprehensive test suite (new file)
3. `docs/SUBSTITUTION_API_FIX.md` - This documentation (new file)

## Related Code

The correct Player model methods are defined in `src/models/player.py`:
- `start_stint(now_ts: float)` - Start a playing stint
- `end_stint(now_ts: float)` - End a playing stint and accumulate time
- `current_stint_seconds(now_ts: float)` - Get current stint duration

## Notes

The frontend JavaScript implementation in `index.html` (lines 1835-1860) uses a different approach but achieves the same result:
- Directly manipulates player properties
- Handles position swaps (when both players are on field)
- Supports queuing multiple substitutions before committing

Both implementations now work correctly and consistently.
