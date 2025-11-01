## Why
- `index.html` bundles HTML, CSS, and JavaScript in a single monolith, making the fast-growing web interface hard to reason about, test, or extend for upcoming strategy tooling.
- There is no asset build pipeline, so we cannot lint, bundle, or version the front-end code; this blocks modularization and modern best practices (ES modules, Sass, etc.).
- Maintaining parallel desktop and web clients would benefit from shared UI modules and automated builds to ensure parity and reduce regressions.

## What Changes
- Introduce a modular web front-end structure that separates templates, styles, and scripts into dedicated directories and files with ES module boundaries.
- Add a lightweight build toolchain (e.g., Vite or esbuild) to bundle assets, support hot reload during development, and emit versioned bundles for Flask to serve.
- Update the Flask app to reference the built assets (with dev vs. prod handling) and adjust repo scripts/documentation accordingly.

## Impact
- Requires new Node-based tooling dependencies and lockfiles; repository setup instructions must cover install/build commands.
- Flask and any deployment scripts must change to serve compiled assets, so testing should confirm no regressions for existing endpoints.
- Provides foundation for future strategy UI and component reuse, reducing code duplication and improving maintainability.

## Acceptance Criteria
- Developers can run documented install/build/watch commands to generate assets without manual edits.
- The Flask app serves the bundled assets in production mode and loads dev-server assets during local development.
- All existing automated tests (`python -m pytest`, `python test_structure.py`) pass after the refactor.
- Web UI loads successfully through `run_web.py`, with modularized templates/scripts/styles producing the current feature set.
