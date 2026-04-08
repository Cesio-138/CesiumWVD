# Electron GUI Guide

CesiumWVD includes a graphical wizard that provides a step-by-step interface for the extraction process.

## Prerequisites

1. **Python backend** must be set up first:
   ```bash
   # From the project root
   ./setup.sh    # Linux/WSL2
   # or
   .\setup.ps1   # Windows
   ```

2. **Node.js 20+** must be installed.

## Development

```bash
cd frontend

# Install dependencies
npm install

# Start in development mode (Vite hot-reload + Electron)
npm run electron:dev
```

This starts three processes concurrently:
- **Vite** dev server on `http://localhost:5174`
- **TypeScript** compiler in watch mode for the Electron files
- **Electron** main process (waits for Vite to be ready)

Changes to React components hot-reload instantly. Changes to Electron main process files require a restart.

## Building

```bash
cd frontend

# Build for distribution
npm run electron:build
```

This produces:
- **Linux**: AppImage in `release/`
- **Windows**: NSIS installer + portable `.exe` in `release/`

### What Gets Bundled

The build (configured in `electron-builder.yml`) bundles:
- Compiled React app (`dist/`)
- Compiled Electron code (`dist-electron/`)
- Python backend source (`src/*.py` → `backend/src/`)
- Portable Python runtime (`.python/` → `backend/.python/`) — includes all DLLs and packages
- Python requirements (`requirements.txt` → `backend/requirements.txt`)

> **Important:** run `.\setup.ps1` / `./setup.sh` from the project root **before** building.
> This downloads a portable Python 3.12 (~60 MB) into `.python/` with all dependencies installed.
> The portable runtime is fully self-contained — the packaged app works on machines without Python.

## How It Works

The Electron app spawns `python -m src.ipc_bridge` as a child process and communicates via JSONL (JSON Lines) over stdin/stdout. See [architecture.md](architecture.md) for the full protocol specification.

The wizard steps map to the 7-step Python pipeline:

| GUI Step | Pipeline Step |
|----------|---------------|
| Welcome | — (user info) |
| Environment | 1. Detect OS |
| Device | 2–4. Prerequisites + AVD + connect |
| Extraction | 5–6. frida + KeyDive |
| Install | 7. Verify + save WVD |
| Done | — (success summary) |
