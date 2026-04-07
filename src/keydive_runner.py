"""
Run KeyDive to extract the Widevine CDM from the device.
"""

import glob
import os
import subprocess
import sys
import shutil
import threading
from pathlib import Path
from typing import Optional

from . import env_detect
from . import drm_trigger
from .ui import info, error, warn, success, fatal


DEFAULT_TIMEOUT = 180  # 3 minutes — CDM init can be slow


def _find_keydive_bin() -> str:
    """Locate the keydive binary inside the local venv or PATH."""
    # 1. Our own venv
    here = Path(__file__).resolve().parent.parent
    venv_bin = here / "venv-wvd" / ("Scripts" if sys.platform == "win32" else "bin") / "keydive"
    if venv_bin.exists():
        return str(venv_bin)
    # On Windows try .exe
    if sys.platform == "win32" and venv_bin.with_suffix(".exe").exists():
        return str(venv_bin.with_suffix(".exe"))
    # 2. PATH
    found = shutil.which("keydive")
    if found:
        return found
    fatal("'keydive' command not found. Did you run setup first?")
    sys.exit(1)


def run_keydive(serial: str, output_dir: Path, timeout: int = DEFAULT_TIMEOUT) -> Optional[Path]:
    """
    Run keydive against the device, streaming output to the user.
    Returns the path to the extracted .wvd file, or None on failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    keydive = _find_keydive_bin()

    cmd = [
        keydive,
        "-s", serial,
        "-o", str(output_dir),
        "-w",           # export as .wvd
        "-a", "player", # use native Kaltura DRM player app (avoids Cloudflare)
    ]

    info(f"Running: {' '.join(cmd)}")
    info(f"Timeout: {timeout}s — waiting for CDM extraction...")
    print()

    # In WSL2 the Windows ADB server is started with -a (0.0.0.0) so it is
    # reachable from WSL2 via the Windows gateway IP (e.g. 172.24.176.1).
    # We must explicitly set ANDROID_ADB_SERVER_ADDRESS to that gateway IP so
    # that keydive's Python ADB client and frida connect to the right server.
    # The value from resolv.conf (10.255.255.254) is a DNS proxy and is NOT
    # routable for ADB; the ip-route gateway IS.
    proc_env = os.environ.copy()
    if env_detect.is_wsl2():
        win_ip = env_detect.get_windows_ip_from_wsl()
        win_adb = env_detect.find_windows_adb_from_wsl()

        if win_ip:
            proc_env["ANDROID_ADB_SERVER_ADDRESS"] = win_ip
            proc_env["ANDROID_ADB_SERVER_PORT"] = "5037"
        else:
            # Can't determine Windows IP; clear any stale/wrong value
            proc_env.pop("ANDROID_ADB_SERVER_ADDRESS", None)
            proc_env.pop("ANDROID_ADB_SERVER_PORT", None)

        if win_adb:
            # Keydive calls 'adb start-server' at startup.  The WSL2 native adb
            # (e.g. 1.0.39) detects a version mismatch with the Windows ADB
            # server (1.0.41) and KILLS it, then fails to restart — taking out
            # our connection.  Work around this by placing an 'adb' shim early
            # in keydive's PATH that calls adb.exe (same version as the server).
            # The shim also unsets the server-address env var so adb.exe uses its
            # Windows default (127.0.0.1:5037) while frida still uses win_ip via
            # the process env variable.
            _wrap_dir = Path("/tmp/wvd-keydive-adb")
            _wrap_dir.mkdir(exist_ok=True)
            _wrap = _wrap_dir / "adb"
            _wrap.write_text(
                "#!/bin/sh\n"
                "unset ANDROID_ADB_SERVER_ADDRESS ANDROID_ADB_SERVER_PORT\n"
                f"exec \"{win_adb}\" \"$@\"\n"
            )
            _wrap.chmod(0o755)
            proc_env["PATH"] = str(_wrap_dir) + ":" + proc_env.get("PATH", os.defpath)

    trigger_fired = False

    def _fire_drm_trigger():
        nonlocal trigger_fired
        import time
        time.sleep(5)
        info("Injecting DRM trigger to provision device and generate key request...")
        try:
            ok = drm_trigger.run_drm_trigger(serial, proc_env)
            trigger_fired = True
            if ok:
                success("DRM trigger completed — keydive should capture the CDM now.")
            else:
                warn("DRM trigger may not have fully completed.")
        except Exception as e:
            warn(f"DRM trigger error: {e}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=proc_env,
        )
        # Stream output with prefix
        trigger_thread = None
        for line in proc.stdout:
            print(f"  [keydive] {line}", end="")
            if "Successfully attached hook" in line and not trigger_fired:
                trigger_thread = threading.Thread(target=_fire_drm_trigger, daemon=True)
                trigger_thread.start()

        proc.wait(timeout=timeout)

        if trigger_thread:
            trigger_thread.join(timeout=30)

        print()

        if proc.returncode == 0:
            success("KeyDive finished successfully.")
        else:
            warn(f"KeyDive exited with code {proc.returncode}.")

    except subprocess.TimeoutExpired:
        proc.kill()
        error(f"KeyDive timed out after {timeout}s.")
        info("The CDM might not have been triggered. Try again or increase timeout.")
        return None

    # Find the .wvd file
    return find_wvd(output_dir)


def find_wvd(output_dir: Path) -> Optional[Path]:
    """Locate any .wvd file in the output directory."""
    wvd_files = sorted(output_dir.glob("**/*.wvd"), key=os.path.getmtime, reverse=True)
    if wvd_files:
        success(f"Found WVD file: {wvd_files[0].name}")
        return wvd_files[0]
    error("No .wvd file found in output directory.")
    info(f"Check the contents of: {output_dir}")
    return None
