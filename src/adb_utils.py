"""
ADB wrapper utilities: device listing, selection, rooting, architecture detection.
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional, List

from .ui import info, warn, error, fatal, success, prompt_choice


@dataclass
class AdbDevice:
    serial: str
    status: str  # "device", "offline", etc.

    @property
    def is_online(self) -> bool:
        return self.status == "device"


def _run(adb: str, *args, device: Optional[str] = None, timeout: int = 10) -> subprocess.CompletedProcess:
    cmd = [adb]
    if device:
        cmd += ["-s", device]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def list_devices(adb: str) -> List[AdbDevice]:
    """Return all ADB-visible devices."""
    try:
        r = _run(adb, "devices")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    devices = []
    for line in r.stdout.strip().splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 2:
            devices.append(AdbDevice(serial=parts[0], status=parts[1]))
    return devices


def select_device(adb: str, forced_serial: Optional[str] = None) -> str:
    """
    Pick a device serial.  If `forced_serial` is given, validate it.
    Otherwise auto-select if one device, or prompt the user.
    """
    devices = list_devices(adb)
    online = [d for d in devices if d.is_online]

    if forced_serial:
        if any(d.serial == forced_serial for d in online):
            info(f"Using specified device: {forced_serial}")
            return forced_serial
        error(f"Device '{forced_serial}' not found or offline.")
        if online:
            info(f"Available devices: {', '.join(d.serial for d in online)}")
        else:
            _no_devices_guidance()
        sys.exit(1)

    if not online:
        _no_devices_guidance()
        sys.exit(1)

    if len(online) == 1:
        info(f"One device found: {online[0].serial}")
        return online[0].serial

    # Multiple devices → prompt
    options = [f"{d.serial}" for d in online]
    idx = prompt_choice("Multiple devices found. Which one?", options)
    return online[idx - 1].serial


def _no_devices_guidance():
    fatal("No Android devices found.")
    info("Make sure one of the following is true:")
    info("  • An Android emulator is running (Android Studio → Device Manager)")
    info("  • A physical device is connected via USB with USB debugging enabled")
    from . import env_detect
    if env_detect.is_wsl2():
        info("  • The ADB port bridge from Windows to WSL2 is set up (see README)")


def root_device(adb: str, serial: str) -> bool:
    """
    Attempt to get root access on the device.
    Returns True if root is confirmed.
    """
    try:
        r = _run(adb, "root", device=serial, timeout=15)
        # "restarting adbd as root" or "adbd is already running as root"
        if "already running as root" in r.stdout:
            success("Device already has root access.")
            return True
        if "restarting" in r.stdout.lower():
            info("Restarting ADB daemon as root...")
            time.sleep(3)
            # Re-check
            r2 = _run(adb, "shell", "whoami", device=serial)
            if "root" in r2.stdout:
                success("Root access confirmed.")
                return True
    except subprocess.TimeoutExpired:
        pass

    # Check if already root without the root command
    try:
        r = _run(adb, "shell", "whoami", device=serial)
        if "root" in r.stdout:
            success("Device already has root access.")
            return True
    except subprocess.TimeoutExpired:
        pass

    error("Could not get root access on this device.")
    info("For emulators: use a 'Google APIs' system image (NOT 'Google Play').")
    info("For physical devices: the device must be rooted (e.g. via Magisk).")
    return False


def get_device_arch(adb: str, serial: str) -> str:
    """
    Get the device CPU architecture mapped to frida naming.
    e.g. x86_64, arm64, x86, arm
    """
    r = _run(adb, "shell", "getprop", "ro.product.cpu.abi", device=serial)
    abi = r.stdout.strip()
    abi_map = {
        "x86_64": "x86_64",
        "x86": "x86",
        "arm64-v8a": "arm64",
        "armeabi-v7a": "arm",
        "armeabi": "arm",
    }
    arch = abi_map.get(abi)
    if not arch:
        fatal(f"Unknown device ABI: '{abi}'. Cannot determine frida-server architecture.")
        sys.exit(1)
    info(f"Device architecture: {abi} → frida-server {arch}")
    return arch


def dismiss_chrome_first_run(adb: str, serial: str) -> None:
    """
    Bypass Chrome's first-run experience on a fresh emulator.

    Chrome shows a "Welcome to Chrome" dialog on first launch that blocks
    navigation. Setting the command-line flag file tells Chrome to skip it.
    """
    flag_file = "/data/local/tmp/chrome-command-line"
    flags = "chrome --disable-fre --no-default-browser-check --no-first-run"
    _run(adb, "shell", f"echo '{flags}' > {flag_file}", device=serial)
    info("Chrome first-run experience bypassed.")


def shell(adb: str, serial: str, cmd: str, timeout: int = 10) -> str:
    """Run a shell command on the device and return stdout."""
    r = _run(adb, "shell", cmd, device=serial, timeout=timeout)
    return r.stdout.strip()


def push_file(adb: str, serial: str, local: str, remote: str):
    """Push a local file to the device."""
    r = _run(adb, "push", local, remote, device=serial, timeout=60)
    if r.returncode != 0:
        error(f"Failed to push {local} → {remote}: {r.stderr.strip()}")
        sys.exit(1)
