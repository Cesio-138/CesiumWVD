#!/usr/bin/env bash
# WVD Extractor — Setup (Linux / WSL2)
# Downloads a portable Python 3.12 and installs all dependencies into .python/.
# .python/ is self-contained so the Electron build works on any Linux machine.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTABLE_PYTHON_DIR="$SCRIPT_DIR/.python"
PYTHON="$PORTABLE_PYTHON_DIR/bin/python3"
PIP="$PORTABLE_PYTHON_DIR/bin/pip"

echo ""
echo "  WVD Extractor — Setup"
echo "  ====================="
echo ""

# ── 1. Ensure portable Python ────────────────────────────────────────────────

if [ -f "$PYTHON" ]; then
    echo "  Portable Python already installed: $("$PYTHON" --version 2>&1)"
    echo ""
else
    echo "  Downloading portable Python 3.12 (~60 MB)..."
    echo ""

    arch=$(uname -m)  # x86_64 or aarch64

    api_url="https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
    release_json=""
    if command -v curl &>/dev/null; then
        release_json=$(curl -fsSL --max-time 20 "$api_url" 2>/dev/null) || true
    elif command -v wget &>/dev/null; then
        release_json=$(wget -qO- --timeout=20 "$api_url" 2>/dev/null) || true
    fi

    dl_url=""
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
                echo "  Install Python manually:  sudo apt install python3 python3-pip"
                exit 1
                ;;
        esac
    fi

    echo "  Downloading: $dl_url"
    mkdir -p "$PORTABLE_PYTHON_DIR"
    tarball="$PORTABLE_PYTHON_DIR/python.tar.gz"

    if command -v curl &>/dev/null; then
        curl -fsSL -L --progress-bar --max-time 300 "$dl_url" -o "$tarball"
    elif command -v wget &>/dev/null; then
        wget --show-progress -q --timeout=300 "$dl_url" -O "$tarball"
    else
        echo "  ERROR: Neither curl nor wget is available."
        echo "  Install Python manually:  sudo apt install python3 python3-pip curl"
        exit 1
    fi

    echo "  Extracting..."
    # python-build-standalone tar has a top-level 'python/' directory
    tar -xzf "$tarball" -C "$PORTABLE_PYTHON_DIR" --strip-components=1
    rm -f "$tarball"

    if [ ! -f "$PYTHON" ]; then
        echo "  ERROR: Portable Python extraction failed (binary not found)."
        exit 1
    fi

    echo "  Portable Python ready: $("$PYTHON" --version 2>&1)"
    echo ""
fi

# ── 2. Install dependencies into .python/ ───────────────────────────────────

echo "  Installing dependencies..."
"$PIP" install --upgrade pip -q
"$PIP" install -r "$SCRIPT_DIR/requirements.txt" -q

echo ""
echo "  ✓ Setup complete!"
echo ""
echo "  Next step: ./extract.sh"
echo ""
