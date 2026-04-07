# Architecture

This document describes the internal architecture of CesiumWVD.

## Overview

CesiumWVD is a 7-step pipeline that extracts a Widevine CDM (`device.wvd`) from an Android device or emulator. It has two frontends (CLI and Electron GUI) sharing the same Python backend.

```
┌──────────────────────┐     ┌─────────────────────────────┐
│   CLI (extract.sh)   │     │   Electron GUI (frontend/)  │
│   Runs src/main.py   │     │   React + Tailwind wizard   │
└─────────┬────────────┘     └──────────┬──────────────────┘
          │                             │
          │ direct calls                │ JSONL over stdin/stdout
          │                             │
          ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Backend (src/)                     │
│                                                             │
│  main.py ─── 7-step orchestrator                            │
│  ipc_bridge.py ─── JSONL IPC entry point                    │
│  ui.py ─── dual-mode output (terminal pretty-print / JSON)  │
│                                                             │
│  env_detect.py ──── Platform detection                      │
│  check_prereqs.py ─ ADB + Python validation                 │
│  avd_manager.py ─── AVD lifecycle                           │
│  adb_utils.py ───── ADB wrapper                             │
│  frida_setup.py ─── frida-server lifecycle                  │
│  keydive_runner.py ─ KeyDive subprocess                     │
│  drm_trigger.py ─── Frida DRM injection                     │
│  wvd_install.py ─── WVD verification + install              │
└─────────────────────────────────────────────────────────────┘
```

## The 7-Step Pipeline

| Step | Module | Description |
|------|--------|-------------|
| 1 | `env_detect.py` | Detect platform: Linux, WSL2, or Windows |
| 2 | `check_prereqs.py` | Verify ADB is available, set up WSL2 port bridge |
| 3 | `avd_manager.py` | Auto-create Android emulator (API 29 google_apis) |
| 4 | `adb_utils.py` | Wait for device boot, get root access |
| 5 | `frida_setup.py` | Download, push, and start frida-server |
| 6 | `keydive_runner.py` + `drm_trigger.py` | Run KeyDive + inject DRM trigger |
| 7 | `wvd_install.py` | Verify `.wvd` file, prompt for install location |

## Dual-Mode Output (`ui.py`)

The `ui.py` module is the key enabler for sharing the pipeline between CLI and GUI:

- **Terminal mode** (default): pretty-prints with colors and step headers
- **IPC mode**: when `ui.enable_ipc_mode()` is called by `ipc_bridge.py`, all output switches to JSONL on stdout and all prompts block on stdin for JSON responses

This means `main.py` contains zero branching for CLI vs. GUI — the same code runs both ways.

## IPC Protocol (Electron ↔ Python)

The Electron main process spawns `python -m src.ipc_bridge` as a child process. Communication is line-delimited JSON (JSONL) over stdin/stdout.

### Frontend → Backend

```json
{"cmd": "start", "options": {"timeout": 180, "output": "/path", ...}}
{"cmd": "respond", "value": "1"}
{"cmd": "respond_confirm", "value": true}
{"cmd": "cancel"}
```

### Backend → Frontend

```json
{"event": "step", "step": 1, "total": 7, "title": "..."}
{"event": "info", "message": "..."}
{"event": "success", "message": "..."}
{"event": "error", "message": "..."}
{"event": "warn", "message": "..."}
{"event": "fatal", "message": "..."}
{"event": "progress", "percent": 45, "label": "..."}
{"event": "prompt_choice", "id": "...", "question": "...", "options": [...], "default": 1}
{"event": "prompt_confirm", "id": "...", "question": "...", "default": true}
{"event": "prompt_path", "id": "...", "question": "..."}
{"event": "log", "message": "..."}
{"event": "done", "wvd_path": "/path/to/device.wvd"}
{"event": "status", "status": "ready|running|finished|error"}
```

## Electron GUI Architecture

```
frontend/
├── electron/
│   ├── main.ts           Electron main process (BrowserWindow, IPC handlers)
│   ├── preload.cts       Context bridge (exposes electronAPI to renderer)
│   └── python-bridge.ts  Spawns Python ipc_bridge.py, parses JSONL stream
└── src/
    ├── App.tsx            Wizard shell — routes between steps, wires backend events
    ├── types.ts           All TypeScript interfaces and event types
    ├── hooks/
    │   └── useBackend.ts  React hook — state machine for backend communication
    └── components/
        ├── steps/         One component per wizard step
        ├── LogViewer.tsx  Scrolling log panel
        ├── ProgressBar.tsx
        ├── PromptOverlay.tsx  Modal for backend prompts
        ├── StepIndicator.tsx
        └── TitleBar.tsx       Custom frameless title bar
```

The `useBackend` hook manages the connection lifecycle:
1. On mount, sets up event listeners via `electronAPI.python.onEvent()`
2. Dispatches events to the appropriate state (step transitions, prompts, logs)
3. Responds to prompts via `electronAPI.python.send()`
