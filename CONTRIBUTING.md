# Contributing to CesiumWVD

Thanks for your interest in contributing! This guide covers the development setup and workflow.

## Development Setup

### Prerequisites

- **Python 3.8+** (3.12 recommended)
- **Node.js 20+** (for the Electron GUI)
- **Android SDK** with API 29 system image (for end-to-end testing)
- **ADB** in your PATH

### Python Backend

```bash
# Create and activate the virtual environment
python3 -m venv venv-wvd
source venv-wvd/bin/activate   # Linux/macOS
# venv-wvd\Scripts\Activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run the CLI
python -m src.main
```

### Electron GUI

```bash
cd frontend

# Install Node.js dependencies
npm install

# Development mode (Vite hot-reload + Electron)
npm run electron:dev

# Production build
npm run electron:build
```

> The GUI relies on the Python venv being set up first — it spawns `src/ipc_bridge.py` as a child process.

## Code Style

### Python

- Follow **PEP 8** conventions
- Line length: **100 characters**
- Linting: `ruff check src/` (config in `pyproject.toml`)
- Target Python version: **3.8** (minimum supported)

### TypeScript / React

- **Strict mode** enabled in `tsconfig.json`
- 2-space indentation
- Type check: `tsc --noEmit` (run from `frontend/`)

## Making Changes

1. **Fork** the repository and create a feature branch from `main`
2. Make your changes with clear, descriptive commits
3. Ensure linting passes:
   ```bash
   ruff check src/
   cd frontend && npx tsc --noEmit
   ```
4. **Test manually** on at least one platform (Linux, WSL2, or Windows)
5. Open a **Pull Request** against `main`

## Pull Request Checklist

- [ ] Code passes `ruff check src/`
- [ ] TypeScript compiles without errors (`tsc --noEmit`)
- [ ] Tested on at least one supported platform
- [ ] Updated documentation if behavior changed
- [ ] Commit messages are clear and descriptive

## Reporting Issues

When filing a bug report, please include:

- **Platform**: Linux / WSL2 / Windows
- **OS version** and architecture
- **Python version**: `python3 --version`
- **ADB version**: `adb --version`
- **Full error output** (copy-paste from terminal)
- **Steps to reproduce**

## Project Structure

See the [File Structure](README.md#file-structure) section in the README and [docs/architecture.md](docs/architecture.md) for a deeper overview.
