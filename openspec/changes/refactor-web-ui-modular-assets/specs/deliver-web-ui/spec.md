## ADDED Requirements
### Requirement: Modular Web UI Assets
Flask web interface MUST consume HTML templates, JavaScript modules, and stylesheets that are authored in separate files instead of a single monolithic `index.html`.

#### Scenario: Template and module separation
- **GIVEN** the Soccer Coach web UI source
- **WHEN** a developer opens the front-end workspace
- **THEN** layout markup resides in reusable templates/partials, JavaScript logic in ES modules, and styles in dedicated stylesheet files.

### Requirement: Front-End Build Pipeline
The project MUST provide a scripted build process that bundles web assets for production and supports a watch mode for development.

#### Scenario: Running the build
- **GIVEN** a developer installs the front-end toolchain
- **WHEN** they run the documented build command
- **THEN** the process outputs versioned assets into the directory served by Flask without manual file editing.

#### Scenario: Development watch mode
- **GIVEN** the developer starts the dev server/watch command
- **WHEN** they modify a front-end module or stylesheet
- **THEN** the tooling rebuilds or hot-reloads the assets so the browser reflects changes without manual restarts.

### Requirement: Flask Asset Integration
Flask MUST load compiled assets in production and fall back to dev-server assets (or unbundled files) during development as documented.

#### Scenario: Production bundle loading
- **GIVEN** a production build has been generated
- **WHEN** the Flask app serves `/`
- **THEN** the rendered HTML references the compiled bundle files so all scripts and styles load successfully.

#### Scenario: Development shortcut
- **GIVEN** the front-end watch mode is running
- **WHEN** Flask is launched in development mode
- **THEN** the app uses the dev-server URLs or unbundled assets, enabling rapid iteration without rebundling manually.
