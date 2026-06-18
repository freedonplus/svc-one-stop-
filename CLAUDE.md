# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OneStopService — a local dev environment service manager. Stack: **Vue 3 + Element Plus + Vite** (frontend), **Python FastAPI** (backend), **Tauri v2** (desktop shell for distribution).

## Key Commands

### Development
```bash
npm run dev              # Vite frontend only
npm run dev:backend      # Python backend only (pythonw, no console)
npm run dev:all          # Vite + Python backend (standard dev workflow)
npm run dev:all:verbose  # Vite + Python with visible console (for debugging)
npm run tauri dev        # Tauri + dev servers (pops a terminal for beforeDevCommand)
```

### Building
```bash
npm run build            # Vite production build
npm run build:backend    # PyInstaller → onestopservice-backend.exe
npm run build:all        # Frontend + backend build
npm run tauri build      # Full Tauri desktop build (runs build:all first)
```

**Note:** PyInstaller is required for `build:backend`. Install with `pip install pyinstaller`.

## Architecture

### Frontend (`src/`)
- **`App.vue`** — Main layout: header stats, toolbar, service grid, log panel, batch bar
- **`components/ServiceCard.vue`** — Single service row: status dot, name, port link, start/stop/log buttons
- **`components/ServiceForm.vue`** — Add/edit service dialog
- **`components/SettingsDialog.vue`** — Theme/font settings + import/export config
- **`components/LogPanel.vue`** — Log viewer with tabbed service switching
- **`components/TitleBar.vue`** — Custom frameless title bar (minimize/maximize/close for Tauri)
- **`api/index.js`** — All HTTP API calls to the backend
- **`constants.js`** — Group definitions, theme options, font config

### Backend (`backend/`)
- **`main.py`** — FastAPI app entry: CORS, router registration, startup console hiding
- **`config.py`** — Services config read/write from `backend/services.json`
- **`process_manager.py`** — Core process management: start/stop/status/port scanning
- **`log_store.py`** — Ring buffer log storage (max 2000 lines per service)
- **`models.py`** — Pydantic models for service config
- **`routers/health.py`** — `GET /api/health`
- **`routers/services.py`** — CRUD: `GET/POST/PUT/DELETE /api/services`
- **`routers/processes.py`** — Start/stop/logs/batch operations
- **`routers/ws.py`** — WebSocket endpoint `/api/ws` for real-time status pushes

### Desktop Shell (`src-tauri/`)
- **`src/lib.rs`** — Tauri setup: spawns backend, tray icon, window management, shutdown cleanup
- **`tauri.conf.json`** — Window config, build commands, bundle settings

## Important Implementation Details

### Service Configuration
Services are stored in **`backend/services.json`**. The backend reads/writes this file directly. Import via the UI Settings dialog calls `POST /api/services` for each service.

### WebSocket Status Pushing
The frontend connects to `ws://localhost:8710/api/ws` on mount. The backend pushes full service status every 5 seconds. If WebSocket fails after 10 retries with exponential backoff, the frontend falls back to HTTP polling every 10 seconds.

### Console Window Hiding
On Windows, all subprocess calls use `DETACHED_PROCESS | CREATE_NO_WINDOW` flags to prevent console window flashing. The `_run_hidden()` helper wraps `subprocess.run` with these flags. Service processes are spawned with `shell=False` on Windows (avoiding `cmd.exe`).

### Backend Lifecycle
- **Dev mode**: Python backend is started by `beforeDevCommand` + `pythonw backend/main.py`
- **Built app**: Tauri spawns `onestopservice-backend.exe` (PyInstaller) or falls back to `pythonw backend/main.py`
- **Cleanup**: `Drop` impl on `BackendProc` + `RunEvent::Exit` handler + `taskkill` brute force ensure backend is killed on exit

### System Process Detection
Instead of running `netstat`/`tasklist` subprocesses (which flash console windows), the backend uses Windows API calls (`GetExtendedTcpTable`, `CreateToolhelp32Snapshot`) via `ctypes`. Results are cached for 2 seconds to avoid redundant scans.

### Window Behavior
- Close button (X) → hides to system tray, does NOT exit
- Tray menu "退出" → kills backend + exits app
- Left-click tray icon → toggles window show/hide
