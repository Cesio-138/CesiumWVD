#!/usr/bin/env bash
# WVD Extractor — Run extraction (Linux / WSL2)
# Runs src/main.py using the portable Python from .python/ (preferred)
# or the virtual environment in venv-wvd/ (legacy fallback).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer portable Python; fall back to venv for backwards compatibility
if [ -f "$SCRIPT_DIR/.python/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/.python/bin/python3"
elif [ -f "$SCRIPT_DIR/venv-wvd/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/venv-wvd/bin/python"
else
    echo ""
    echo "  ERROR: Python environment not found."
    echo "  Run setup first:  ./setup.sh"
    echo ""
    exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/src/main.py" "$@"
