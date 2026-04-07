#!/usr/bin/env bash
# WVD Extractor — Setup (Linux / WSL2)
# Creates a virtual environment and installs dependencies.
# If Python >= 3.8 is not found, downloads a portable Python 3.12 automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv-wvd"
PORTABLE_PYTHON_DIR="$SCRIPT_DIR/.python"

echo ""
echo "  WVD Extractor — Setup"
echo "  ====================="
echo ""

# ── 1. Find or download Python ───────────────────────────────────────────────

PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ -n "$major" ] && [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

_download_portable_python() {
    echo "  Python >= 3.8 not found. Downloading a portable Python 3.12 (~60 MB)..."
    echo ""

    local arch
    arch=$(uname -m)  # x86_64 or aarch64

    # Try to resolve the latest release URL from GitHub API
    local api_url="https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
    local release_json=""
    if command -v curl &>/dev/null; then
        release_json=$(curl -fsSL --max-time 20 "$api_url" 2>/dev/null) || true
    elif command -v wget &>/dev/null; then
        release_json=$(wget -qO- --timeout=20 "$api_url" 2>/dev/null) || true
    fi

    local dl_url=""
    if [ -n "$release_json" ]; then
        dl_url=$(printf '%s' "$release_json" \
            | grep -o '"browser_download_url" *: *"[^"]*"' \
            | grep 'install_only\.tar\.gz' \
            | grep "$arch" \
            | grep 'linux-gnu' \
            | grep -v 'freethreaded' \
            | head -1 \
            | grep -o '"https://[^"]*"' \
            | tr -d '"') || true
    fi

    # Hardcoded fallback (python-build-standalone 20260325, Python 3.12.13)
    if [ -z "$dl_url" ]; then
        case "$arch" in
            x86_64)
                dl_url="https://github.com/astral-sh/python-build-standalone/releases/download/20260325/cpython-3.12.13%2B20260325-x86_64-unknown-linux-gnu-install_only.tar.gz"
                ;;
            aarch64|arm64)
                dl_url="https://github.com/astral-sh/python-build-standalone/releases/download/20260325/cpython-3.12.13%2B20260325-aarch64-unknown-linux-gnu-install_only.tar.gz"
                ;;
            *)
                echo "  ERROR: Unsupported architecture: $arch"
                echo "  Install Python manually:  sudo apt install python3 python3-venv"
                exit 1
                ;;
        esac
    fi

    echo "  Downloading: $dl_url"
    mkdir -p "$PORTABLE_PYTHON_DIR"
    local tarball="$PORTABLE_PYTHON_DIR/python.tar.gz"

    if command -v curl &>/dev/null; then
        curl -fsSL -L --progress-bar --max-time 300 "$dl_url" -o "$tarball"
    elif command -v wget &>/dev/null; then
        wget --show-progress -q --timeout=300 "$dl_url" -O "$tarball"
    else
        echo "  ERROR: Neither curl nor wget is available."
        echo "  Install Python manually:  sudo apt install python3 python3-venv"
        exit 1
    fi

    echo "  Extracting..."
    # python-build-standalone tar has a top-level 'python/' directory
    tar -xzf "$tarball" -C "$PORTABLE_PYTHON_DIR" --strip-components=1
    rm -f "$tarball"

    PYTHON="$PORTABLE_PYTHON_DIR/bin/python3"
    if [ ! -f "$PYTHON" ]; then
        echo "  ERROR: Portable Python extraction failed (binary not found)."
        exit 1
    fi
    echo "  ✓ Portable Python ready: $($PYTHON --version)"
    echo ""
}

if [ -z "$PYTHON" ]; then
    _download_portable_python
fi

echo "  Using: $PYTHON ($($PYTHON --version 2>&1))"

# ── 2. Create virtual environment ────────────────────────────────────────────

if [ -d "$VENV_DIR" ]; then
    echo "  Virtual environment already exists: $VENV_DIR"
    echo "  To recreate, delete it first: rm -rf $VENV_DIR"
else
    echo "  Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# ── 3. Install dependencies ─────────────────────────────────────────────────

echo "  Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

echo ""
echo "  ✓ Setup complete!"
echo ""
echo "  Next step: ./extract.sh"
echo ""
