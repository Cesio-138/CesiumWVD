"""
Prerequisite checks: Python version, ADB availability, WSL2 bridge.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from . import env_detect
from .ui import command_block, error, fatal, info, success, warn

# Well-known SDK platform-tools locations per OS
_ADB_SEARCH_PATHS = []
if env_detect.is_windows():
    _local = Path(
        __import__("os").environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    )
    _ADB_SEARCH_PATHS = [
        _local / "Android" / "Sdk" / "platform-tools" / "adb.exe",
    ]
else:
    _ADB_SEARCH_PATHS = [
        Path.home() / "Android" / "Sdk" / "platform-tools" / "adb",
        Path("/usr/lib/android-sdk/platform-tools/adb"),
    ]


def find_adb() -> Optional[str]:
    """Locate the adb binary. Returns the path string or None."""
    # In WSL2, always prefer the Windows adb.exe over the WSL2 native adb.
    # Both are on different versions and cannot talk to the same server;
    # using adb.exe directly avoids the portproxy and version-mismatch entirely.
    if env_detect.is_wsl2():
        win_adb = env_detect.find_windows_adb_from_wsl()
        if win_adb:
            return win_adb

    # 1. PATH (native OS or WSL2 fallback when Windows binary not found)
    found = shutil.which("adb")
    if found:
        return found
    # 2. Well-known locations (native OS)
    for p in _ADB_SEARCH_PATHS:
        if p.exists():
            return str(p)
    return None


def check_python_version():
    v = sys.version_info
    if v < (3, 8):
        fatal(f"Python >= 3.8 is required (you have {v.major}.{v.minor}.{v.micro}).")
        sys.exit(1)


def check_adb() -> str:
    """Find adb or exit with clear guidance."""
    adb = find_adb()
    if adb:
        info(f"ADB found: {adb}")
        return adb

    error("ADB (Android Debug Bridge) not found.")
    if env_detect.is_windows():
        info("Install Android Studio or download Platform Tools from:")
        info("  https://developer.android.com/tools/releases/platform-tools")
    elif env_detect.is_wsl2():
        info("ADB must be available inside WSL2. Two options:")
        info("  a) Install adb in WSL2: sudo apt install adb")
        info("  b) Or install Android Studio on Windows (ADB bridge setup will follow)")
    else:
        info("Install adb: sudo apt install adb  (or install Android Studio)")
    sys.exit(1)


def check_wsl2_bridge(adb: str):
    """
    If in WSL2, configure the ADB env and test connectivity.
    If we're using the Windows adb.exe directly, no portproxy is needed.
    """
    if not env_detect.is_wsl2():
        return

    # If we found the Windows adb.exe (WSL path ending in .exe), use it directly.
    # It talks to the Windows ADB server on localhost — no portproxy needed.
    if adb.endswith(".exe"):
        info("Using Windows adb.exe from WSL2 — no portproxy bridge needed.")

        # Kill any WSL2-native adb fork-server competing on port 5037.
        # The native adb (e.g. 1.0.39) and Windows adb.exe (e.g. 1.0.41) speak
        # different protocol versions. If the native server is bound to port 5037,
        # Windows adb.exe gets "protocol fault (couldn't read status)" on every call.
        wsl_adb = shutil.which("adb")
        if wsl_adb and not wsl_adb.endswith(".exe"):
            try:
                subprocess.run(["pkill", "-f", "fork-server"], capture_output=True, timeout=3)
            except Exception:
                pass

        # Check for a Windows portproxy rule on port 5037.  A leftover rule from
        # a previous WSL2 bridge attempt makes iphlpsvc (svchost) own port 5037,
        # which prevents the Windows ADB server from ever binding to that port.
        # Every adb.exe call then gets "protocol fault" because it connects to the
        # portproxy daemon instead of a real ADB server.
        try:
            proxy_result = subprocess.run(
                ["powershell.exe", "-Command", "netsh interface portproxy show all"],
                capture_output=True, text=True, timeout=8,
            )
            if "5037" in proxy_result.stdout:
                error("A Windows portproxy rule on port 5037 is blocking the Windows ADB server.")
                info("This leftover rule was created by a previous WSL2 bridge attempt and is")
                info("no longer needed — Windows adb.exe now talks directly to the ADB server.")
                info("")
                info("Remove it by running this command in an Administrator PowerShell (once):")
                command_block(
                    "netsh interface portproxy delete v4tov4 listenport=5037 listenaddress=0.0.0.0 && netsh interface portproxy delete v4tov4 listenport=5555 listenaddress=0.0.0.0",
                    "Administrator PowerShell — remove old ADB portproxy rules (run once, then Re-check)",
                )
                sys.exit(1)
        except Exception:
            pass

        # (Re)start the Windows ADB server with -a (all interfaces).
        # Default start-server only binds to 127.0.0.1 (Windows loopback), which
        # is NOT reachable from WSL2.  With -a the server binds to 0.0.0.0, making
        # it accessible at the Windows gateway IP (e.g. 172.x.x.1) from WSL2 —
        # required so that keydive/frida can connect to the device.
        try:
            subprocess.run([adb, "kill-server"], capture_output=True, timeout=10)
        except Exception:
            pass
        try:
            subprocess.run([adb, "-a", "start-server"], capture_output=True, timeout=15)
        except Exception:
            pass

        try:
            result = subprocess.run(
                [adb, "devices"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [line for line in result.stdout.strip().splitlines() if "\tdevice" in line]
            if lines:
                success(f"ADB connected — {len(lines)} device(s) visible.")
            else:
                warn("No devices visible yet. Make sure the emulator is running on Windows.")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            warn("Could not reach ADB server. Make sure the Android emulator is running.")
        return

    win_ip = env_detect.configure_adb_env_for_wsl2()
    if not win_ip:
        warn("Could not determine Windows host IP from /etc/resolv.conf.")
        warn("ADB bridge to Windows emulator may not work.")
        return

    info(f"WSL2 detected. Configured ADB to reach Windows at {win_ip}:5037")

    # Test connectivity
    try:
        result = subprocess.run(
            [adb, "devices"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [line for line in result.stdout.strip().splitlines() if "\tdevice" in line]
        if lines:
            success("ADB bridge working — device(s) visible from WSL2.")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    warn("ADB bridge to Windows appears to be down.")
    info("Run this command in a Windows PowerShell (as Administrator):")
    command_block(
        'netsh interface portproxy add v4tov4 listenport=5037 listenaddress=0.0.0.0 connectport=5037 connectaddress=127.0.0.1',
        'Run as Administrator in Windows PowerShell',
    )
    info("Then make sure the Android emulator is running on Windows.")
    info("To verify the bridge, run this in a Windows terminal:")
    # Try to find the Windows adb.exe so we can give an exact verification command
    win_adb = env_detect.find_windows_adb_from_wsl()
    if win_adb:
        win_adb_path = '"' + win_adb.replace("/mnt/c", "C:").replace("/", "\\") + '"'
        command_block(win_adb_path + " kill-server && " + win_adb_path + " devices", 'Windows terminal — restart ADB server then list devices')
    else:
        command_block('adb kill-server && adb devices', 'Windows terminal — restart ADB server then list devices')
        info("  (adb.exe is in Android SDK \\platform-tools — add it to your Windows PATH if not found)")
    info("You should see your emulator listed. Then click Re-check below.")
    sys.exit(1)


def run_all_checks() -> str:
    """Run all prerequisite checks. Returns the adb path."""
    check_python_version()
    adb = check_adb()
    check_wsl2_bridge(adb)
    return adb


def preflight_check() -> dict:
    """
    Non-fatal prerequisite probe for the GUI pre-flight banner.

    Returns:
        {"ok": True, "missing": []}
        {"ok": False, "missing": ["adb", "sdk"]}   # one or both can be missing
    """
    missing = []

    # ADB
    adb = find_adb()
    if not adb:
        missing.append("adb")

    # Android SDK emulator (avdmanager / emulator binary)
    # Import lazily to avoid a hard dependency at module level
    try:
        from . import avd_manager  # noqa: PLC0415
        sdk_ok, _ = avd_manager.is_available()
        if not sdk_ok:
            missing.append("sdk")
    except Exception:
        missing.append("sdk")

    return {"ok": len(missing) == 0, "missing": missing}
