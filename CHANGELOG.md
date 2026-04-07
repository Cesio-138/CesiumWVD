# Changelog

All notable changes to CesiumWVD will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-04-07

### Added

- Automated Widevine CDM (`device.wvd`) extraction pipeline (7-step flow)
- Platform detection for Linux, WSL2, and Windows
- Android emulator auto-creation with API 29 `google_apis` system image
- frida-server auto-download, push, and lifecycle management
- KeyDive integration with configurable timeout
- WVD file verification via pywidevine (optional)
- CLI interface (`extract.sh` / `extract.ps1`) with flags: `--device`, `--no-create`, `--keep-avd`, `--timeout`, `--output`
- Setup scripts (`setup.sh` / `setup.ps1`) with auto Python download
- WSL2 ↔ Windows ADB port bridge detection and guidance
- Electron GUI wizard (React + Tailwind) with step-by-step flow
- IPC bridge (JSONL protocol) between Electron and Python backend
- Smart caching for frida-server binaries (`~/.cache/CesiumWVD/`)
