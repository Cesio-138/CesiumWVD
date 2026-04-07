#!/usr/bin/env bash
# WVD Extractor — Run extraction (Linux / WSL2)
# Activates the venv and runs src/main.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv-wvd"
PYTHON="$VENV_DIR/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo ""
    echo "  ERROR: Virtual environment not found."
    echo "  Run setup first:  ./setup.sh"
    echo ""
    exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/src/main.py" "$@"
