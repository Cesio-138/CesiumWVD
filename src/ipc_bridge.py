#!/usr/bin/env python3
"""
JSONL IPC bridge for the Electron frontend.

Reads JSON commands from stdin, runs the extraction pipeline,
and emits structured JSON events to stdout.

Protocol:
  Frontend → Backend:
    {"cmd": "start", "options": {"timeout": 180, "output": "/path", ...}}
    {"cmd": "respond", "value": "1"}
    {"cmd": "respond_confirm", "value": true}
    {"cmd": "cancel"}

  Backend → Frontend:
    {"event": "step", "step": 1, "total": 7, "title": "..."}
    {"event": "info|success|error|warn|fatal", "message": "..."}
    {"event": "progress", "percent": 45, "label": "..."}
    {"event": "prompt_choice", "id": "...", "question": "...", "options": [...], "default": 1}
    {"event": "prompt_confirm", "id": "...", "question": "...", "default": true}
    {"event": "prompt_path", "id": "...", "question": "..."}
    {"event": "log", "message": "..."}
    {"event": "done", "wvd_path": "/path/to/device.wvd"}
    {"event": "status", "status": "ready|running|finished|error"}
"""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

# Ensure src/ is importable
_here = Path(__file__).resolve().parent
if str(_here.parent) not in sys.path:
    sys.path.insert(0, str(_here.parent))

from src import (  # noqa: E402
    adb_utils,
    avd_manager,
    check_prereqs,
    drm_trigger,
    env_detect,
    frida_setup,
    keydive_runner,
    ui,
    wvd_install,
)

TOTAL_STEPS = 7


def _emit(obj: dict):
    """Write a JSON event to stdout."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _read_command() -> Optional[dict]:
    """Read one JSON command from stdin, or None on EOF."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line.strip())
    except (json.JSONDecodeError, EOFError):
        return None


def run_extraction(options: dict):
    """
    Main extraction pipeline — mirrors main.py but emits JSONL events.
    """
    timeout = options.get("timeout", 180)
    output_dir = Path(options.get("output", str(_here.parent / "cdm-output")))
    forced_serial = options.get("device")
    no_create = options.get("noCreate", False)
    keep_avd = options.get("keepAvd", False)

    auto_created_serial = None

    try:
        # ── Step 1: Environment ──────────────────────────────────────────
        ui.step(1, TOTAL_STEPS, "Detecting environment")
        platform_label = env_detect.get_platform_label()
        ui.success(f"Platform: {platform_label}")
        if env_detect.is_wsl2():
            ui.info("WSL2 mode: will bridge ADB to the Windows host automatically.")

        # ── Step 2: Prerequisites ────────────────────────────────────────
        ui.step(2, TOTAL_STEPS, "Checking prerequisites")
        check_prereqs.check_python_version()
        ui.success("Python version OK")

        adb = check_prereqs.check_adb()
        # check_adb does sys.exit(1) on failure — which we'll catch

        if env_detect.is_wsl2():
            check_prereqs.check_wsl2_bridge(adb)

        ui.success("All prerequisites met.")

        # ── Step 3: Device / Emulator ────────────────────────────────────
        ui.step(3, TOTAL_STEPS, "Setting up Android device")
        serial = None

        if forced_serial:
            ui.info(f"Using specified device: {forced_serial}")
            serial = forced_serial
        else:
            devices = adb_utils.list_devices(adb)
            online = [d for d in devices if d.is_online]

            if online and no_create:
                ui.info(f"Found {len(online)} device(s) already running.")
            elif online:
                choice = ui.prompt_choice(
                    f"{len(online)} device(s) already connected. What would you like to do?",
                    [
                        f"Use existing: {online[0].serial}" if len(online) == 1
                        else f"Select from {len(online)} devices",
                        "Create a new temporary emulator instead",
                    ],
                    default=1,
                )
                if choice == 2:
                    online = []

            if not online and not serial:
                available, reason = avd_manager.is_available()
                if available and not no_create:
                    ui.info("No device connected — creating a temporary Android emulator...")
                    auto_created_serial = avd_manager.setup_emulator(adb)
                    if not auto_created_serial:
                        ui.fatal("Failed to start emulator automatically.")
                        _emit({"event": "status", "status": "error"})
                        return
                    serial = auto_created_serial
                else:
                    msg = reason if reason else "No devices found and --no-create was specified."
                    ui.error(f"Cannot auto-create emulator: {msg}")
                    ui.info("Please start an Android emulator manually, then retry.")
                    _emit({"event": "status", "status": "error"})
                    return

        # ── Step 4: Connect & Root ───────────────────────────────────────
        ui.step(4, TOTAL_STEPS, "Connecting to Android device")
        serial = adb_utils.select_device(adb, forced_serial=serial)
        if not adb_utils.root_device(adb, serial):
            ui.fatal("Root access is required. Use a Google APIs image (not Google Play).")
            _emit({"event": "status", "status": "error"})
            return
        ui.success(f"Connected to {serial} with root access.")

        # ── Step 5: Frida ────────────────────────────────────────────────
        ui.step(5, TOTAL_STEPS, "Setting up frida-server")
        frida_setup.ensure_frida_server(adb, serial)

        # Dismiss Chrome's first-run dialog so the DRM test page can load
        adb_utils.dismiss_chrome_first_run(adb, serial)

        # ── Step 6: KeyDive ──────────────────────────────────────────────
        ui.step(6, TOTAL_STEPS, "Extracting Widevine CDM")
        ui.info("This may take 1-2 minutes. KeyDive will trigger a DRM test...")

        wvd_path = _run_keydive_ipc(serial, output_dir, timeout)
        if not wvd_path:
            ui.fatal("CDM extraction failed.")
            ui.info("Common fixes: ensure emulator has internet, try --timeout 300")
            if auto_created_serial and not keep_avd:
                avd_manager.kill_emulator(adb, auto_created_serial)
                avd_manager.delete_avd()
            _emit({"event": "status", "status": "error"})
            return

        # ── Step 7: Verify & Install ─────────────────────────────────────
        ui.step(7, TOTAL_STEPS, "Verifying and installing WVD file")
        if not wvd_install.verify_wvd(wvd_path):
            ui.fatal("The extracted WVD file could not be verified.")
            _emit({"event": "status", "status": "error"})
            return

        wvd_install.install_wvd(wvd_path)

        # ── Cleanup ──────────────────────────────────────────────────────
        if auto_created_serial:
            if keep_avd:
                ui.info("Keeping temporary emulator (--keep-avd was set).")
            else:
                if ui.confirm("Shut down and delete the temporary emulator?", default=True):
                    ui.info("Shutting down emulator...")
                    avd_manager.kill_emulator(adb, auto_created_serial)
                    avd_manager.delete_avd()

        _emit({"event": "done", "wvd_path": str(wvd_path)})
        _emit({"event": "status", "status": "finished"})

    except SystemExit as e:
        # Backend modules call sys.exit(1) on fatal errors
        ui.fatal(f"Process exited with code {e.code}")
        _emit({"event": "status", "status": "error"})
    except Exception as e:
        ui.fatal(f"Unexpected error: {e}")
        _emit({"event": "status", "status": "error"})


def _run_keydive_ipc(serial: str, output_dir: Path, timeout: int) -> Optional[Path]:
    """
    Run keydive, streaming its output as log events.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    keydive = keydive_runner._find_keydive_bin()

    cmd = [keydive, "-s", serial, "-o", str(output_dir), "-w", "-a", "player"]
    ui.info(f"Running: {' '.join(cmd)}")

    # ── WSL2 env setup ────────────────────────────────────────────────────────
    # In WSL2 with Windows adb.exe:
    #  - ADB server is started with -a so it listens on 0.0.0.0:5037 (Windows).
    #  - The Windows gateway IP (e.g. 172.24.176.1) is the only route from WSL2
    #    to that server; resolv.conf nameserver (10.255.255.254) is DNS-only.
    #  - Keydive's Remote.__init__ calls `adb start-server` using the WSL2 native
    #    adb (1.0.39) which detects the version mismatch (server=1.0.41) and KILLS
    #    the server, then fails to restart it at a remote host.
    #  Fix: (a) prepend an 'adb' shim to PATH that delegates to adb.exe (matching
    #  version, no kill); (b) set ANDROID_ADB_SERVER_ADDRESS to the gateway IP
    #  so frida connects to the right server.
    proc_env = os.environ.copy()
    if env_detect.is_wsl2():
        win_ip = env_detect.get_windows_ip_from_wsl()
        win_adb = env_detect.find_windows_adb_from_wsl()

        if win_ip:
            proc_env["ANDROID_ADB_SERVER_ADDRESS"] = win_ip
            proc_env["ANDROID_ADB_SERVER_PORT"] = "5037"
        else:
            proc_env.pop("ANDROID_ADB_SERVER_ADDRESS", None)
            proc_env.pop("ANDROID_ADB_SERVER_PORT", None)

        if win_adb:
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

        ui.info(f"[ADB bridge] server={proc_env.get('ANDROID_ADB_SERVER_ADDRESS','?')} adb={win_adb or 'native'}")

    trigger_fired = False

    def _fire_drm_trigger():
        """Run the DRM trigger in a background thread after keydive hooks are ready."""
        nonlocal trigger_fired
        import time
        time.sleep(5)  # Give the Kaltura app time to fully start
        ui.info("Injecting DRM trigger to provision device and generate key request...")
        try:
            ok = drm_trigger.run_drm_trigger(serial, proc_env)
            trigger_fired = True
            if ok:
                ui.success("DRM trigger completed — keydive should capture the CDM now.")
            else:
                ui.warn("DRM trigger may not have fully completed.")
        except Exception as e:
            ui.warn(f"DRM trigger error: {e}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=proc_env,
        )

        trigger_thread = None
        for line in proc.stdout:
            ui.log(f"  [keydive] {line}")
            # After keydive hooks are attached, fire the DRM trigger
            if "Successfully attached hook" in line and not trigger_fired:
                trigger_thread = threading.Thread(target=_fire_drm_trigger, daemon=True)
                trigger_thread.start()

        proc.wait(timeout=timeout)

        if trigger_thread:
            trigger_thread.join(timeout=30)

        if proc.returncode == 0:
            ui.success("KeyDive finished successfully.")
        else:
            ui.warn(f"KeyDive exited with code {proc.returncode}.")

    except subprocess.TimeoutExpired:
        proc.kill()
        ui.error(f"KeyDive timed out after {timeout}s.")
        return None

    return keydive_runner.find_wvd(output_dir)


def main():
    """Entry point: enable IPC mode, wait for start command, run pipeline."""
    ui.enable_ipc_mode()
    _emit({"event": "status", "status": "ready"})

    while True:
        cmd = _read_command()
        if cmd is None:
            break  # stdin closed

        action = cmd.get("cmd", "")

        if action == "start":
            _emit({"event": "status", "status": "running"})
            run_extraction(cmd.get("options", {}))
        elif action == "preflight":
            result = check_prereqs.preflight_check()
            _emit({"event": "preflight_result", "ok": result["ok"], "missing": result["missing"]})
        elif action == "ping":
            _emit({"event": "pong"})
        elif action == "quit":
            break


if __name__ == "__main__":
    main()
