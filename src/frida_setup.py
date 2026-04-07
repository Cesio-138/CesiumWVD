"""
Download, push, and start frida-server on an Android device.
"""

import lzma
import os
import sys
import time
import urllib.request
from pathlib import Path

from . import adb_utils
from .ui import error, info, success, warn

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "CesiumWVD"
REMOTE_PATH = "/data/local/tmp/frida-server"


def get_frida_version() -> str:
    import frida
    return frida.__version__


def is_frida_running(adb: str, serial: str) -> bool:
    out = adb_utils.shell(adb, serial, "ps -A 2>/dev/null || ps", timeout=5)
    return "frida-server" in out


def _download_url(version: str, arch: str) -> str:
    return (
        f"https://github.com/frida/frida/releases/download/{version}/"
        f"frida-server-{version}-android-{arch}.xz"
    )


def download_frida_server(version: str, arch: str) -> Path:
    """Download frida-server binary (with local cache). Returns the local file path."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"frida-server-{version}-android-{arch}"

    if cached.exists():
        info(f"Using cached frida-server: {cached.name}")
        return cached

    url = _download_url(version, arch)
    xz_path = cached.with_suffix(".xz")
    info(f"Downloading frida-server {version} for {arch}...")
    info(f"  URL: {url}")

    try:
        urllib.request.urlretrieve(url, str(xz_path))
    except Exception as e:
        error(f"Download failed: {e}")
        info("Check your internet connection and try again.")
        sys.exit(1)

    # Decompress .xz
    info("Extracting...")
    try:
        with lzma.open(str(xz_path), "rb") as xz_in:
            with open(str(cached), "wb") as out:
                out.write(xz_in.read())
        xz_path.unlink()
    except Exception as e:
        error(f"Extraction failed: {e}")
        xz_path.unlink(missing_ok=True)
        cached.unlink(missing_ok=True)
        sys.exit(1)

    success(f"Downloaded: {cached.name}")
    return cached


def push_and_start(adb: str, serial: str, local_path: Path):
    """Push frida-server to the device and start it."""
    info("Pushing frida-server to device...")
    adb_utils.push_file(adb, serial, str(local_path), REMOTE_PATH)
    adb_utils.shell(adb, serial, f"chmod 755 {REMOTE_PATH}")

    # Kill any existing frida-server first
    adb_utils.shell(adb, serial, "pkill -f frida-server 2>/dev/null; true")
    time.sleep(1)

    # Start in background
    info("Starting frida-server on device...")
    adb_utils.shell(adb, serial, f"{REMOTE_PATH} -D &")
    time.sleep(2)

    if is_frida_running(adb, serial):
        success("frida-server is running.")
    else:
        warn("frida-server may not have started correctly. KeyDive will attempt to connect anyway.")


def ensure_frida_server(adb: str, serial: str):
    """Full pipeline: check if running → download if needed → push & start."""
    version = get_frida_version()
    info(f"Frida version: {version}")

    if is_frida_running(adb, serial):
        success("frida-server is already running on the device.")
        return

    arch = adb_utils.get_device_arch(adb, serial)
    local = download_frida_server(version, arch)
    push_and_start(adb, serial, local)
