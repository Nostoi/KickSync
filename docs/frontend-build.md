# Web Front-End Build & Development Guide

The Soccer Coach Sideline Timekeeper web UI is now a modular front-end built with [Vite](https://vitejs.dev/). This document explains how to install dependencies, run the development server, and build assets for Flask to serve.

## Prerequisites

- Node.js 18+ (LTS recommended)
- npm (bundled with Node.js)

## One-Time Setup

```bash
cd frontend
npm install
```

This installs all JavaScript dependencies and generates `package-lock.json`.

## Development Workflow

1. Start the Vite dev server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Export the dev server URL so Flask loads unbundled assets with hot reloading:
   ```bash
   export WEB_UI_DEV_SERVER="http://localhost:5173"
   ```

3. Launch the Flask backend in another terminal:
   ```bash
   python run_web.py
   ```

With `WEB_UI_DEV_SERVER` set, the Flask app serves templates that point to the Vite dev server. Changes to files in `frontend/src/` hot-reload automatically.

## Production Build

```bash
cd frontend
npm run build
```

This command outputs compiled assets and a Vite manifest to `web_dist/`. The Flask app automatically reads `web_dist/manifest.json` and references the hashed bundle filenames.

After building, unset `WEB_UI_DEV_SERVER` (or start a new shell) before running `python run_web.py` so Flask serves the compiled assets:

```bash
unset WEB_UI_DEV_SERVER
python run_web.py
```

## Verification Checklist

- `npm run build` completes without errors.
- `python run_web.py` loads the web UI and uses bundled assets (check browser dev tools for `/static/web_dist/…` URLs).
- `python test_structure.py` and `python -m pytest` still pass.
- Optional: `npm run dev` + `WEB_UI_DEV_SERVER` enables hot reload for local development.
