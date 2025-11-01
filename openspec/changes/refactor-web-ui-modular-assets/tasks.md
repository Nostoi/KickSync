## Implementation
- [ ] Audit current `index.html` assets and document components that need extraction.
- [ ] Introduce front-end build tooling (scaffold package.json, configure Vite/esbuild, add npm scripts).
- [ ] Break HTML into templates/partials and move CSS/JS into modular files wired through the bundler.
- [ ] Update Flask `web_app` static serving logic to differentiate dev/prod bundles and ensure cache busting.
- [ ] Adjust deployment docs/scripts to include front-end build steps and add verification instructions.

## Validation
- [ ] Run `openspec validate refactor-web-ui-modular-assets --strict`.
- [ ] Execute front-end build and confirm assets load successfully via `run_web.py`.
- [ ] Run existing Python test suite (`python -m pytest` and `python test_structure.py`).
