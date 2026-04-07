# CLI Guide

CesiumWVD runs fully from the command line — no GUI required. Useful for automation, headless servers, or scripting.

## Setup (one time)

### Linux / WSL2

```bash
cd CesiumWVD
chmod +x setup.sh extract.sh
./setup.sh
```

### Windows (PowerShell)

```powershell
cd CesiumWVD
.\setup.ps1
```

This creates a Python virtual environment (`venv-wvd/`) with all dependencies. If Python 3.8+ isn't found, it automatically downloads a portable Python 3.12.

## Running

```bash
./extract.sh        # Linux / WSL2
.\extract.ps1       # Windows
```

The emulator is created and started automatically if the Android SDK is found.

## Options

| Flag | Default | Description |
|---|---|---|
| `--device <serial>` | auto | Use a specific ADB device serial instead of auto-detecting |
| `--no-create` | off | Skip emulator auto-creation; require an existing connected device |
| `--keep-avd` | off | Don't delete the temporary emulator after extraction |
| `--timeout <seconds>` | `180` | Time to wait for KeyDive to complete |
| `--output <path>` | `./cdm-output` | Directory to save the extracted WVD file |

### Examples

```bash
# Use an already-running emulator (skip auto-create)
./extract.sh --no-create

# Use a specific device by serial
./extract.sh --device 192.168.1.50:5555

# Keep the emulator running after extraction
./extract.sh --keep-avd

# Slow machine — give KeyDive more time
./extract.sh --timeout 300

# Save WVD to a specific directory
./extract.sh --output ~/widevine
```

## WSL2 Setup

The Android emulator runs as a Windows process. WSL2 cannot reach it by default — you need to forward ADB port 5037 **once**.

Run in a **Windows PowerShell as Administrator**:

```powershell
netsh interface portproxy add v4tov4 listenport=5037 listenaddress=0.0.0.0 connectport=5037 connectaddress=127.0.0.1
```

The script prints this exact command and exits if the bridge isn't detected. To make it permanent, schedule it as a startup task.

Verify with `adb devices` in a Windows terminal — the emulator should appear after it boots.

> If you previously set up this bridge and it's no longer needed (CesiumWVD now uses `adb.exe` directly from WSL2 when available), remove the old rule to avoid port conflicts:
> ```powershell
> netsh interface portproxy delete v4tov4 listenport=5037 listenaddress=0.0.0.0
> ```

## Cleanup

After extraction the emulator and AVD are deleted automatically. To free everything:

```bash
rm -rf ~/.cache/CesiumWVD      # Cached frida-server downloads
rm -rf /path/to/CesiumWVD      # Project directory (includes venv-wvd/)
```

The Android system image (~1.4 GB) stays in your SDK — remove it via Android Studio → SDK Manager.

## Physical Device (Rooted)

To use a rooted Android phone instead of an emulator:

1. Enable **USB Debugging**: Settings → Developer Options → USB Debugging ON
2. Connect via USB and approve the debugging prompt on the phone
3. Verify: `adb devices` should show the device as `device` (not `unauthorized`)
4. Run:
   ```bash
   ./extract.sh --no-create --device <serial>
   ```

The device must have root access (e.g., via [Magisk](https://github.com/topjohnwu/Magisk)). Grant root when prompted by `adb root`.
