"""
Programmatic Android Virtual Device (AVD) management.

Creates, starts, and optionally deletes a temporary AVD for CDM extraction.
Works by writing AVD config files directly — no avdmanager needed.

Supported on:
  - Linux (native): uses ~/Android/Sdk
  - WSL2: writes to Windows paths (/mnt/c/...) and calls emulator.exe
  - Windows: uses %LOCALAPPDATA%\Android\Sdk (from PowerShell entry point)
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional, Tuple, List

from . import env_detect
from .ui import info, warn, error, success, confirm


AVD_NAME = "wvd_extractor_tmp"
AVD_DISPLAY_NAME = "WVD Extractor (temporary)"

# Prefer API 29 Google APIs — ideal for CDM extraction (allows root, no PlayStore lock)
PREFERRED_IMAGES = [
    ("android-29", "google_apis", "x86_64"),
    ("android-29", "google_apis", "x86"),
    ("android-30", "google_apis", "x86_64"),
    ("android-28", "google_apis", "x86_64"),
    ("android-28", "google_apis", "x86"),
    ("android-33", "google_apis", "x86_64"),
]

# System-image download
_SYSIMG_BASE_URL = "https://dl.google.com/android/repository/sys-img/google_apis/"
_SYSIMG_MANIFEST_URL = _SYSIMG_BASE_URL + "sys-img2-3.xml"
# SHA-1 of the Android SDK License text — written to sdk/licenses/android-sdk-license
_SDK_LICENSE_HASH = "24333f8a63b6825ea9c5514f83c2829b004d1fee"


# ─── SDK Discovery ────────────────────────────────────────────────────────────

def _wsl2_windows_user() -> Optional[str]:
    """Find the Windows username from /mnt/c/Users/ in WSL2."""
    users_dir = Path("/mnt/c/Users")
    skip = {"Public", "Default", "Default User", "All Users",
            "Todos os Usuários", "Usuário Padrão"}
    if not users_dir.exists():
        return None
    for d in users_dir.iterdir():
        if d.name in skip or d.name.startswith("."):
            continue
        if d.is_dir():
            # Prefer the one that has an Android SDK
            if (d / "AppData" / "Local" / "Android" / "Sdk").exists():
                return d.name
    # Fallback: pick first non-system user
    for d in users_dir.iterdir():
        if d.name not in skip and not d.name.startswith(".") and d.is_dir():
            return d.name
    return None


def find_sdk_root() -> Optional[Path]:
    """Locate the Android SDK root directory."""
    # 1. Explicit env vars
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        v = os.environ.get(env)
        if v and Path(v).exists():
            return Path(v)

    if env_detect.is_wsl2():
        win_user = _wsl2_windows_user()
        if win_user:
            candidate = Path(f"/mnt/c/Users/{win_user}/AppData/Local/Android/Sdk")
            if candidate.exists():
                return candidate

    elif env_detect.is_windows():
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidate = local / "Android" / "Sdk"
        if candidate.exists():
            return candidate

    else:  # Linux native
        candidates = [
            Path.home() / "Android" / "Sdk",
            Path.home() / "android" / "sdk",
            Path("/usr/lib/android-sdk"),
        ]
        for c in candidates:
            if c.exists():
                return c

    return None


def find_system_image(sdk_root: Path) -> Optional[Tuple[str, str, str]]:
    """
    Return the best (api_level, tag, arch) tuple for CDM extraction,
    preferring API 29 Google APIs x86_64.
    """
    images_root = sdk_root / "system-images"
    if not images_root.exists():
        return None

    for api, tag, arch in PREFERRED_IMAGES:
        img_path = images_root / api / tag / arch
        if img_path.exists():
            return (api, tag, arch)
    return None


def find_emulator_bin(sdk_root: Path) -> Optional[str]:
    """Find the emulator binary."""
    candidates = []
    if env_detect.is_wsl2():
        # Call the Windows emulator binary from WSL2
        candidates.append(sdk_root / "emulator" / "emulator.exe")
    elif env_detect.is_windows():
        candidates.append(sdk_root / "emulator" / "emulator.exe")
    else:
        candidates.append(sdk_root / "emulator" / "emulator")

    for c in candidates:
        if c.exists():
            return str(c)

    # Fallback: PATH
    found = shutil.which("emulator")
    return found


# ─── AVD Home ────────────────────────────────────────────────────────────────

def get_avd_home() -> Tuple[Path, str]:
    """
    Returns (avd_home_path, windows_style_path_or_empty).

    For Linux: (Path("~/.android/avd"), "")
    For WSL2:  (Path("/mnt/c/Users/<user>/.android/avd"), "C:\\Users\\<user>\\.android\\avd")
    For Win:   (Path("C:/Users/.../.android/avd"), same Windows style)
    """
    if env_detect.is_wsl2():
        win_user = _wsl2_windows_user()
        if win_user:
            avd_home = Path(f"/mnt/c/Users/{win_user}/.android/avd")
            win_path = f"C:\\Users\\{win_user}\\.android\\avd"
            return avd_home, win_path

    if env_detect.is_windows():
        home = Path.home()
        avd_home = home / ".android" / "avd"
        win_path = str(avd_home).replace("/", "\\")
        return avd_home, win_path

    return Path.home() / ".android" / "avd", ""


# ─── AVD Creation ────────────────────────────────────────────────────────────

def _build_image_sysdir(sdk_root: Path, api: str, tag: str, arch: str) -> str:
    """Build the image.sysdir.1 value (backslash for Windows/WSL2, forward for Linux)."""
    rel = ["system-images", api, tag, arch, ""]  # trailing sep = required by emulator
    if env_detect.is_wsl2() or env_detect.is_windows():
        return "\\".join(rel)
    return "/".join(rel)


def _build_avd_dir_path(avd_home: Path, win_avd_home: str) -> Tuple[str, str, str]:
    """
    Returns (avd_dir_path_ini, avd_dir_path_rel, avd_dir_linux_path).
    The first two are for the .ini file. Third is the actual filesystem path.
    """
    avd_dir_linux = str(avd_home / f"{AVD_NAME}.avd")
    if env_detect.is_wsl2() or env_detect.is_windows():
        ini_path = win_avd_home.rstrip("\\") + f"\\{AVD_NAME}.avd"
        rel_path = f"avd\\{AVD_NAME}.avd"
    else:
        ini_path = str(avd_home / f"{AVD_NAME}.avd")
        rel_path = f"avd/{AVD_NAME}.avd"
    return ini_path, rel_path, avd_dir_linux


def create_avd(sdk_root: Path, api: str, tag: str, arch: str) -> bool:
    """
    Create a temporary AVD by writing config files directly.
    Returns True on success.
    """
    avd_home, win_avd_home = get_avd_home()
    avd_home.mkdir(parents=True, exist_ok=True)

    avd_dir = avd_home / f"{AVD_NAME}.avd"
    avd_ini = avd_home / f"{AVD_NAME}.ini"

    # Clean up any leftovers
    delete_avd(silent=True)

    avd_dir.mkdir(parents=True, exist_ok=True)

    ini_path, rel_path, _ = _build_avd_dir_path(avd_home, win_avd_home)
    target_api = int(api.replace("android-", ""))

    # Write outer .ini
    ini_content = (
        f"avd.ini.encoding=UTF-8\n"
        f"path={ini_path}\n"
        f"path.rel={rel_path}\n"
        f"target=android-{target_api}\n"
    )
    avd_ini.write_text(ini_content, encoding="utf-8")

    # Build image.sysdir.1
    sysdir = _build_image_sysdir(sdk_root, api, tag, arch)
    tag_display = "Google APIs" if tag == "google_apis" else tag.replace("_", " ").title()

    # Write config.ini
    config_content = (
        f"AvdId = {AVD_NAME}\n"
        f"PlayStore.enabled = false\n"
        f"abi.type = {arch}\n"
        f"avd.ini.displayname = {AVD_DISPLAY_NAME}\n"
        f"avd.ini.encoding = UTF-8\n"
        f"disk.dataPartition.size = 2147483648\n"
        f"fastboot.forceChosenSnapshotBoot = no\n"
        f"fastboot.forceColdBoot = yes\n"
        f"fastboot.forceFastBoot = no\n"
        f"hw.accelerometer = yes\n"
        f"hw.arc = false\n"
        f"hw.audioInput = no\n"
        f"hw.battery = yes\n"
        f"hw.camera.back = none\n"
        f"hw.camera.front = none\n"
        f"hw.cpu.arch = {arch}\n"
        f"hw.cpu.ncore = 4\n"
        f"hw.dPad = no\n"
        f"hw.gps = yes\n"
        f"hw.gpu.enabled = yes\n"
        f"hw.gpu.mode = auto\n"
        f"hw.initialOrientation = portrait\n"
        f"hw.keyboard = yes\n"
        f"hw.lcd.density = 420\n"
        f"hw.lcd.height = 1920\n"
        f"hw.lcd.width = 1080\n"
        f"hw.mainKeys = no\n"
        f"hw.ramSize = 2048\n"
        f"hw.sdCard = no\n"
        f"hw.sensors.orientation = yes\n"
        f"hw.sensors.proximity = yes\n"
        f"hw.trackBall = no\n"
        f"image.sysdir.1 = {sysdir}\n"
        f"runtime.network.latency = none\n"
        f"runtime.network.speed = full\n"
        f"showDeviceFrame = no\n"
        f"skin.dynamic = yes\n"
        f"skin.name = 1080x1920\n"
        f"tag.display = {tag_display}\n"
        f"tag.id = {tag}\n"
        f"vm.heapSize = 512\n"
    )
    (avd_dir / "config.ini").write_text(config_content, encoding="utf-8")

    success(f"AVD '{AVD_NAME}' created (API {target_api}, {tag}, {arch})")
    return True


# ─── System Image Download ────────────────────────────────────────────────────

def _write_sdk_license(sdk_root: Path) -> None:
    """Record license acceptance in the SDK's licenses directory."""
    lic_dir = sdk_root / "licenses"
    lic_dir.mkdir(exist_ok=True)
    lic_file = lic_dir / "android-sdk-license"
    existing = lic_file.read_text(encoding="utf-8") if lic_file.exists() else ""
    if _SDK_LICENSE_HASH not in existing:
        with open(lic_file, "a", encoding="utf-8") as f:
            f.write(f"\n{_SDK_LICENSE_HASH}\n")


def _find_sysimg_url(api: str, arch: str) -> Optional[str]:
    """Fetch the Google APIs manifest and return the zip download URL."""
    try:
        req = urllib.request.Request(
            _SYSIMG_MANIFEST_URL,
            headers={"User-Agent": "wvd-extractor/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        target_path = f"system-images;{api};google_apis;{arch}"
        for pkg in root.iter():
            if pkg.tag.split("}")[-1] == "remotePackage" and pkg.get("path") == target_path:
                for child in pkg.iter():
                    tag_name = child.tag.split("}")[-1]
                    if tag_name == "url" and child.text and child.text.endswith(".zip"):
                        return _SYSIMG_BASE_URL + child.text
    except Exception:
        pass
    return None


def download_system_image(sdk_root: Path, api: str, tag: str, arch: str) -> bool:
    """
    Download and install a Google APIs system image into the SDK (~1.3 GB).
    Shows a license prompt before downloading.
    Returns True on success.
    """
    info(f"System image not found: {api}/{tag}/{arch}")
    info("It can be downloaded automatically (~1.3 GB).")
    print()
    warn("This requires accepting the Android SDK License Agreement.")
    info("Full license text: https://developer.android.com/studio/terms")
    print()
    if not confirm("Download system image and accept the License Agreement?", default=False):
        error("License not accepted. Cannot download system image.")
        return False

    url = _find_sysimg_url(api, arch)
    if not url:
        api_num = api.replace("android-", "")
        error("Could not locate system image download URL from Google's manifest.")
        info("Install manually: Android Studio → SDK Manager → SDK Platforms")
        info(f"  → Android {api_num}.0 (API {api_num}) → Google APIs → {arch} → Install")
        return False

    info(f"Downloading: {url}")
    dest_dir = sdk_root / "system-images" / api / tag / arch
    dest_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_zip_str = tempfile.mkstemp(suffix=".zip", prefix="wvd_sysimg_")
    os.close(fd)
    tmp_zip = Path(tmp_zip_str)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "wvd-extractor/1.0"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(tmp_zip, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 // total
                        mb_done = done // (1024 * 1024)
                        mb_total = total // (1024 * 1024)
                        label = f"Downloading system image... {mb_done}/{mb_total} MB"
                        from .ui import progress as ui_progress
                        ui_progress(pct, label)
                        print(
                            f"\r  Downloading... {pct}%  ({mb_done}/{mb_total} MB)   ",
                            end="",
                            flush=True,
                        )
        print()

        info("Extracting system image...")
        with zipfile.ZipFile(tmp_zip) as zf:
            members = zf.namelist()
            # Strip the common leading directory (e.g. "x86_64/") if present
            prefix = ""
            if members and "/" in members[0]:
                candidate = members[0].split("/")[0] + "/"
                if all(m.startswith(candidate) or m == candidate for m in members):
                    prefix = candidate
            for member in members:
                if member.endswith("/"):
                    continue
                rel = member[len(prefix):] if prefix else member
                if not rel:
                    continue
                target = dest_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())

        _write_sdk_license(sdk_root)
        success(f"System image installed: {dest_dir}")
        return True

    except Exception as exc:
        print()
        error(f"Download failed: {exc}")
        # Remove empty dest_dir if we created it
        if dest_dir.exists() and not any(dest_dir.iterdir()):
            dest_dir.rmdir()
        return False
    finally:
        tmp_zip.unlink(missing_ok=True)


# ─── Emulator Lifecycle ───────────────────────────────────────────────────────

def _get_known_serials(adb: str) -> List[str]:
    try:
        r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=5)
        return [l.split()[0] for l in r.stdout.splitlines()[1:] if "\t" in l]
    except Exception:
        return []


def _to_windows_path(wsl_path: str) -> str:
    """Convert a WSL2 /mnt/c/... path to a Windows C:\... path."""
    try:
        return subprocess.check_output(
            ["wslpath", "-w", wsl_path],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        # Fallback: simple string replacement
        if wsl_path.startswith("/mnt/c/"):
            return "C:\\" + wsl_path[7:].replace("/", "\\")
        return wsl_path


def start_emulator(emulator_bin: str) -> subprocess.Popen:
    """Start the emulator in the background and return the process."""
    cmd = [emulator_bin, "-avd", AVD_NAME, "-no-audio", "-no-boot-anim"]
    info(f"Starting emulator: {' '.join(cmd)}")
    info("  The emulator will boot — this usually takes 1-2 minutes...")

    if env_detect.is_wsl2():
        # In WSL2, emulator.exe is a Windows binary.
        # Use PowerShell Start-Process to launch it as a detached Windows GUI process.
        win_emu = _to_windows_path(emulator_bin)
        args_str = f"-avd {AVD_NAME} -no-audio -no-boot-anim"
        ps_cmd = f'Start-Process -WindowStyle Hidden -FilePath "{win_emu}" -ArgumentList "{args_str}"'
        proc = subprocess.Popen(
            ["powershell.exe", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=10)
        if proc.returncode != 0:
            error("PowerShell failed to start the emulator.")
    else:
        # Linux or Windows: start detached normally
        kwargs = {}
        if sys.platform != "win32":
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )

    return proc


def wait_for_boot(adb: str, serial: str, timeout: int = 180) -> bool:
    """Poll until the emulator has fully booted. Returns True on success."""
    from .ui import progress as ui_progress
    deadline = time.time() + timeout
    start = time.time()
    info(f"  Waiting for device '{serial}' to finish booting (up to {timeout}s)...")

    while time.time() < deadline:
        try:
            r = subprocess.run(
                [adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip() == "1":
                ui_progress(100, "Emulator fully booted.")
                success("Emulator has finished booting.")
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass
        elapsed = int(time.time() - start)
        pct = min(95, elapsed * 100 // timeout)
        ui_progress(pct, f"Waiting for boot... ({elapsed}s / {timeout}s)")
        time.sleep(3)

    return False


def find_new_serial(adb: str, known_serials: List[str], timeout: int = 120) -> Optional[str]:
    """
    Wait for a new emulator serial to appear in `adb devices`.
    Returns the new serial or None if timed out.
    """
    from .ui import progress as ui_progress
    deadline = time.time() + timeout
    info("  Waiting for emulator to register with ADB...")
    start = time.time()

    while time.time() < deadline:
        try:
            r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines()[1:]:
                if "\t" in line:
                    serial, status = line.split("\t", 1)
                    if serial.strip() not in known_serials and "emulator" in serial:
                        print()
                        return serial.strip()
        except Exception:
            pass
        elapsed = int(time.time() - start)
        pct = min(95, elapsed * 100 // timeout)
        ui_progress(pct, f"Waiting for emulator to appear in ADB... ({elapsed}s / {timeout}s)")
        time.sleep(2)

    print()
    return None


def kill_emulator(adb: str, serial: str):
    """Gracefully shut down the emulator."""
    try:
        subprocess.run(
            [adb, "-s", serial, "emu", "kill"],
            capture_output=True, timeout=10,
        )
        time.sleep(2)
    except Exception:
        pass


def delete_avd(silent: bool = False):
    """Remove the temporary AVD files."""
    avd_home, _ = get_avd_home()
    avd_dir = avd_home / f"{AVD_NAME}.avd"
    avd_ini = avd_home / f"{AVD_NAME}.ini"

    deleted = False
    if avd_dir.exists():
        shutil.rmtree(avd_dir, ignore_errors=True)
        deleted = True
    if avd_ini.exists():
        avd_ini.unlink(missing_ok=True)
        deleted = True

    if deleted and not silent:
        success(f"Temporary AVD '{AVD_NAME}' deleted.")
    elif not deleted and not silent:
        info("No temporary AVD found to delete.")


# ─── High-Level Orchestrator ──────────────────────────────────────────────────

def is_available() -> Tuple[bool, str]:
    """
    Check if auto-create is possible on this system.
    Returns (available, reason_if_not).

    A missing system image is NOT a blocker — it can be downloaded automatically.
    """
    sdk = find_sdk_root()
    if not sdk:
        return False, (
            "Android SDK not found. Install Android Studio (https://developer.android.com/studio) "
            "or set the ANDROID_HOME environment variable."
        )

    emu = find_emulator_bin(sdk)
    if not emu:
        return False, (
            "Android Emulator binary not found in your SDK. "
            "Install it via Android Studio → SDK Manager → SDK Tools → Android Emulator."
        )

    # System image can be downloaded automatically if missing — considered available
    return True, ""


def setup_emulator(adb: str) -> Optional[str]:
    """
    Full pipeline: (download image if missing) → create AVD → start emulator → wait for boot.
    Returns the ADB serial of the booted emulator, or None on failure.
    """
    sdk = find_sdk_root()
    emu = find_emulator_bin(sdk)

    img = find_system_image(sdk)
    if not img:
        # No system image found — offer to download it automatically
        if not download_system_image(sdk, "android-29", "google_apis", "x86_64"):
            return None
        img = ("android-29", "google_apis", "x86_64")

    api, tag, arch = img

    info(f"Android SDK: {sdk}")
    info(f"System image: {api} / {tag} / {arch}")
    info(f"Emulator: {emu}")

    # Record existing serials so we can identify the new one
    known = _get_known_serials(adb)

    if not create_avd(sdk, api, tag, arch):
        return None

    proc = start_emulator(emu)

    # Wait for it to appear in adb devices
    print()
    serial = find_new_serial(adb, known, timeout=120)

    if not serial:
        # Fallback: the emulator may have been pre-started or already registered
        warn("No new emulator appeared within 120s. Checking for any running emulator...")
        try:
            r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines()[1:]:
                if "\t" in line:
                    s, st = line.split("\t", 1)
                    if "emulator" in s and st.strip() in ("device", "offline"):
                        serial = s.strip()
                        info(f"Found emulator already registered: {serial}")
                        break
        except Exception:
            pass

    if not serial:
        error("Emulator didn't appear in ADB within 120s.")
        info("It may still be starting. Check if the emulator window opened on Windows.")
        return None

    success(f"Emulator serial: {serial}")

    # Wait for full boot
    booted = wait_for_boot(adb, serial, timeout=180)
    if not booted:
        error("Emulator didn't finish booting in time.")
        info("Try running the extraction manually once the emulator boots.")
        return None

    return serial
