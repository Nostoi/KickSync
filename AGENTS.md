# AGENTS.md - Autonomous Agent Instructions

**Project:** Soccer Coach Sideline Timekeeper  
**Purpose:** Instructions for autonomous agents to execute tasks from app-analysis-and-improvement-plan.md  
**Target:** Codex and other AI autonomous agents  

## Overview

This document provides structured instructions for autonomous agents to understand, prioritize, and execute the improvement tasks outlined in `docs/app-analysis-and-improvement-plan.md`. The project is a **Soccer Coach Sideline Timekeeper** - a dual-interface application (Tkinter desktop + Flask web) for managing player rotations and equal playing time in youth soccer.

## Project Status

### ✅ **Completed (Phase 1 Foundation)**
- **Modular Structure**: Successfully refactored into `src/` directory structure
- **Code Organization**: Models, services, UI, and utils properly separated
- **Backward Compatibility**: Legacy entry points (`coach_timer.py`, `app.py`) maintained
- **Documentation**: Comprehensive docstrings and type hints added
- **Verification**: All functionality preserved and tested

### 📋 **Ready for Execution**
The project is now ready for autonomous agents to execute Phase 2 and Phase 3 improvements.

## Agent Execution Framework

### 1. Task Identification Process

When executing tasks from the improvement plan:

```python
# Agent Decision Tree
def identify_next_task(current_phase, completed_tasks):
    """
    Priority order for task execution:
    1. HIGH: Phase 1 items (if any remaining)
    2. MEDIUM: Phase 2 Feature Enhancements  
    3. LOW: Phase 3 Advanced Features
    """
    if current_phase == "Phase 1":
        return get_foundation_tasks()
    elif current_phase == "Phase 2":
        return get_enhancement_tasks()
    else:
        return get_advanced_tasks()
```

### 2. Task Categories & Instructions

#### **Phase 2: Feature Enhancements (CURRENT PRIORITY)**

**2.1 Advanced Timer Features**
```yaml
Priority: HIGH
Files to modify:
  - src/services/timer_service.py
  - src/utils/constants.py
  - src/ui/tkinter_app.py (timer controls)
  - src/ui/web_app.py (API endpoints)

Tasks:
  - stoppage_time: Add injury time tracking to TimerService
  - multiple_periods: Support configurable game formats
  - custom_game_length: Make GAME_LENGTH_MIN configurable
  - time_adjustments: Enhance manual correction interface

Implementation Notes:
  - Maintain backward compatibility with existing game states
  - Add new fields to GameState model if needed
  - Update both Tkinter and web interfaces
  - Add comprehensive tests for new timer logic
```

**2.2 Enhanced Player Management**
```yaml
Priority: MEDIUM
Files to modify:
  - src/models/player.py (extend Player model)
  - src/services/player_service.py (create new service)
  - src/ui/tkinter_app.py (player forms)
  - index.html (web player management)

Tasks:
  - player_profiles: Extend Player model with photos, contact, medical
  - skill_ratings: Add position-specific skill tracking
  - attendance_tracking: Track game-by-game attendance
  - player_statistics: Add goals, assists, disciplinary data

Implementation Strategy:
  - Extend existing Player dataclass with new optional fields
  - Create PlayerService for business logic
  - Add new UI screens/dialogs for extended data entry
  - Ensure JSON persistence handles new fields gracefully
```

**2.3 Team Strategy Tools**
```yaml
Priority: MEDIUM
Files to create/modify:
  - src/services/strategy_service.py (new)
  - src/models/formation.py (new)
  - src/ui/formation_editor.py (new)

Tasks:
  - formation_builder: Visual formation editor with drag-drop
  - substitution_planning: Pre-game substitution strategy
  - position_rotation: AI-driven rotation suggestions
  - opponent_scouting: Team notes and tactical planning

Technical Requirements:
  - Create Formation model for tactical setups
  - Build StrategyService for game planning logic
  - Add visual formation editor to both UI implementations
  - Integrate with existing substitution system
```

**2.4 Data Analytics**
```yaml
Priority: HIGH (High business value)
Files to create/modify:
  - src/services/analytics_service.py (new)
  - src/models/game_report.py (new)
  - src/ui/reports_view.py (new)

Tasks:
  - playing_time_reports: Detailed per-player/game/season analytics
  - performance_metrics: Track improvement trends
  - team_balance: Position coverage and fairness analysis
  - export_capabilities: CSV/PDF report generation

Data Requirements:
  - Historical game data storage
  - Statistical calculations and trending
  - Visualization components (charts/graphs)
  - Export functionality with multiple formats
```

#### **Phase 3: Advanced Features (FUTURE)**

**3.1 Communication Hub**
```yaml
Priority: LOW
Dependencies: External services (SMS, email)
Files to create:
  - src/services/notification_service.py
  - src/integrations/sms_provider.py
  - src/integrations/email_provider.py

Implementation Notes:
  - Requires external API integrations
  - Consider privacy/COPPA compliance for youth sports
  - Optional feature with clear user consent
```

**3.2 League Management**
```yaml
Priority: LOW  
Complexity: HIGH
Files to create:
  - src/models/league.py
  - src/models/tournament.py
  - src/services/league_service.py

Implementation Notes:
  - Major architectural change
  - Requires multi-tenancy support
  - Consider as separate application/module
```

## Agent Execution Guidelines

### Code Quality Standards

```python
# Required for all agent-generated code
STANDARDS = {
    "type_hints": "All functions must have complete type annotations",
    "docstrings": "Google-style docstrings for all public methods",
    "error_handling": "Robust exception handling with specific error types",
    "testing": "Unit tests for all new functionality",
    "backward_compatibility": "Must not break existing functionality"
}
```

### Testing Requirements

```bash
# Agent must run these commands after any changes
python test_structure.py           # Verify structure integrity
python -m pytest tests/           # Run all unit tests (when created)
python run_desktop.py             # Manual verification - desktop app
python run_web.py                 # Manual verification - web app
```

### File Modification Patterns

**When modifying existing files:**
1. **Read entire file** to understand context
2. **Preserve existing functionality** completely
3. **Add new features** as extensions, not replacements
4. **Update imports** and dependencies as needed
5. **Add comprehensive docstrings** for new methods
6. **Maintain backward compatibility** with existing data

**When creating new files:**
1. **Follow existing patterns** from similar files in the project
2. **Use proper imports** from the established structure
3. **Include comprehensive error handling**
4. **Add type hints throughout**
5. **Create corresponding test files** in `tests/` directory

### Integration Points

**Critical integration points to respect:**

```python
# Core models - extend carefully
src/models/player.py          # Player data structure
src/models/game_state.py      # Game state management

# Core services - integrate with
src/services/timer_service.py      # Game timing logic
src/services/persistence_service.py # Data persistence

# UI integration points
src/ui/tkinter_app.py         # Desktop interface
src/ui/web_app.py             # Web interface
index.html                    # Web frontend
```

### Data Persistence Strategy

**Current system:** JSON-based persistence via `PersistenceService`

**Agent guidelines:**
- **Extend JSON schema** for new data fields
- **Maintain backward compatibility** with existing save files
- **Add migration logic** if schema changes significantly
- **Consider SQLite migration** for complex analytics (Phase 2.4)

### UI Development Patterns

**Tkinter Desktop (src/ui/tkinter_app.py):**
```python
# Pattern for adding new views
class NewFeatureView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()
    
    def _build_ui(self):
        # Build interface components
        pass
    
    def on_show(self):
        # Called when view becomes active
        self.refresh()
    
    def refresh(self):
        # Update display with current data
        pass
```

**Web Interface (index.html + web_app.py):**
```html
<!-- Pattern for new web features -->
<div class="panel" id="new-feature-panel">
  <div class="section-title">New Feature</div>
  <!-- Feature content -->
</div>

<script>
// JavaScript for feature interaction
function handleNewFeature() {
  // Implementation
}
</script>
```

## Agent Decision Matrix

### Task Selection Criteria

| Factor | Weight | Considerations |
|--------|---------|---------------|
| **Business Value** | 40% | Direct benefit to coaches/players |
| **Implementation Complexity** | 30% | Development effort required |
| **Risk Level** | 20% | Potential to break existing functionality |
| **Dependencies** | 10% | External services or major refactoring needed |

### Implementation Priority

```python
TASK_PRIORITY = {
    "Phase 2.4 - Data Analytics": "HIGHEST",      # High value, moderate complexity
    "Phase 2.1 - Advanced Timer": "HIGH",         # Core feature enhancement
    "Phase 2.2 - Player Management": "MEDIUM",    # Useful but complex
    "Phase 2.3 - Strategy Tools": "MEDIUM",       # Nice-to-have features
    "Phase 3.x - Advanced Features": "LOW"        # Future considerations
}
```

## Debugging and Validation

### Required Validation Steps

```bash
# Agent must execute these steps after any modification
cd /path/to/soccer_coach

# 1. Structure verification
python test_structure.py

# 2. Import verification
python -c "from src import *; print('All imports successful')"

# 3. Functionality verification
python run_desktop.py &  # Test desktop app
python run_web.py &      # Test web app

# 4. Legacy compatibility
python coach_timer.py &  # Test legacy desktop
python app.py &          # Test legacy web
```

### Common Pitfalls for Agents

1. **Breaking Backward Compatibility**
   - Always test legacy entry points
   - Don't modify existing method signatures
   - Extend, don't replace existing functionality

2. **Incomplete Error Handling**
   - Wrap file operations in try/catch
   - Handle missing dependencies gracefully
   - Provide meaningful error messages

3. **Ignoring Existing Patterns**
   - Study existing code structure before adding new features
   - Follow established naming conventions
   - Maintain consistency with existing UI patterns

4. **Inadequate Testing**
   - Test both Tkinter and web interfaces
   - Verify data persistence works correctly
   - Check edge cases and error conditions

## Success Criteria

### For Each Task Completion

```yaml
Definition of Done:
  - ✅ Feature implemented according to specification
  - ✅ All existing functionality preserved
  - ✅ Both UI interfaces updated (desktop + web)
  - ✅ Comprehensive error handling added
  - ✅ Type hints and docstrings complete
  - ✅ Structure verification test passes
  - ✅ Manual testing completed successfully
  - ✅ Backward compatibility maintained
```

### Project Health Metrics

```python
HEALTH_METRICS = {
    "functionality_preservation": "100%",  # No regression
    "test_coverage": ">80%",               # When test suite created
    "documentation_coverage": "100%",      # All public methods documented
    "type_annotation_coverage": "100%",   # All functions typed
    "backward_compatibility": "100%"      # Legacy entry points work
}
```

## Agent Communication Protocol

### Progress Reporting

When executing tasks, agents should provide updates in this format:

```markdown
## Task Progress Report

**Task:** [Task Name from improvement plan]
**Phase:** [1/2/3]
**Status:** [In Progress/Completed/Blocked]
**Files Modified:** [List of files changed]
**Testing Status:** [Pass/Fail/Not Started]
**Backward Compatibility:** [Verified/Issues Found]
**Next Steps:** [What's next or blockers encountered]
```

### Error Reporting

```markdown
## Error Report

**Task:** [Task Name]
**Error Type:** [Import/Runtime/Logic/UI]
**Error Message:** [Specific error encountered]
**Files Involved:** [Files that caused the issue]
**Attempted Fixes:** [What was tried]
**Resolution Needed:** [What's needed to proceed]
```

---

**This document serves as the primary guide for autonomous agents working on the Soccer Coach Sideline Timekeeper project. Follow these instructions to ensure successful task execution while maintaining the application's reliability and user experience.**