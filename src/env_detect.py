"""
Platform and environment detection utilities.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    return sys.platform == "win32"


def is_wsl2() -> bool:
    """Detect if running inside WSL2 (Linux under Windows)."""
    if is_windows():
        return False
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def get_windows_ip_from_wsl() -> Optional[str]:
    """
    Return the Windows host IP reachable from WSL2.

    Prefers the default-route gateway (e.g. 172.24.176.1 from 'ip route'),
    which is the vEthernet (WSL) adapter — services bound to 0.0.0.0 on
    Windows are accessible there.

    Falls back to the /etc/resolv.conf nameserver (10.255.255.254) which is a
    DNS-relay address; it works for DNS but the Windows ADB server is NOT
    reachable on that IP unless portproxy rules are active.
    """
    # Primary: default-route gateway — this is the real Windows bridge IP
    try:
        r = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=3,
        )
        for line in r.stdout.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    # Fallback: /etc/resolv.conf nameserver
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if line.strip().startswith("nameserver"):
                    return line.split()[1]
    except (FileNotFoundError, IndexError):
        pass
    return None


def configure_adb_env_for_wsl2() -> Optional[str]:
    """
    If running in WSL2, set environment variables so adb reaches the
    Windows-side ADB server.  Returns the Windows IP used, or None if
    not applicable.
    """
    if not is_wsl2():
        return None

    ip = get_windows_ip_from_wsl()
    if ip:
        os.environ["ANDROID_ADB_SERVER_ADDRESS"] = ip
        os.environ["ANDROID_ADB_SERVER_PORT"] = "5037"
    return ip


def find_windows_adb_from_wsl() -> Optional[str]:
    """
    From inside WSL2, locate the Windows adb.exe on the host filesystem.

    Strategy:
      1. Ask cmd.exe where adb is (respects the Windows PATH).
      2. Fall back to scanning well-known install locations under every
         user profile in /mnt/c/Users/.

    Returns the WSL-compatible path (e.g. /mnt/c/Users/…/adb.exe) or None.
    """
    if not is_wsl2():
        return None

    # 1. Ask Windows cmd.exe — fast and respects PATH
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "where adb 2>nul"],
            capture_output=True, timeout=5, encoding="cp1252", errors="replace",
        )
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.lower().endswith("adb.exe"):
                # Convert Windows path → WSL path via wslpath
                try:
                    wsl = subprocess.run(
                        ["wslpath", "-u", line],
                        capture_output=True, text=True, timeout=3,
                    )
                    wsl_path = wsl.stdout.strip()
                    if wsl_path and Path(wsl_path).exists():
                        return wsl_path
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 2. Scan well-known locations under every Windows user profile
    users_root = Path("/mnt/c/Users")
    if users_root.is_dir():
        _common_rel = [
            Path("AppData") / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path("AppData") / "Local" / "Programs" / "Android" / "platform-tools" / "adb.exe",
        ]
        try:
            for user_dir in sorted(users_root.iterdir()):
                if not user_dir.is_dir() or user_dir.name in ("Public", "Default", "All Users"):
                    continue
                for rel in _common_rel:
                    candidate = user_dir / rel
                    if candidate.exists():
                        return str(candidate)
        except PermissionError:
            pass

    return None


def get_platform_label() -> str:
    if is_windows():
        return "Windows"
    if is_wsl2():
        return "WSL2 (Linux under Windows)"
    return "Linux"


def get_cesio_data_dir() -> Path:
    """Return the Cesio-138 data directory (mirrors backend/config.py logic)."""
    env_dir = os.environ.get("CESIO_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Cesio-138"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "cesio-138"
