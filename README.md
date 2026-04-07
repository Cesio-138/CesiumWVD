# WVD Extractor

Automated tool to extract a Widevine CDM (`device.wvd`) from an Android device.

This is a **one-time process**. Once you have the `.wvd` file, you won't need to do this again.

---

## What You Need

### Option A: Android Emulator (Recommended — fully automated)

The script handles **everything automatically**. You only need the Android SDK installed.

| Requirement | Details |
|---|---|
| **Android SDK** | Install [Android Studio](https://developer.android.com/studio) (SDK + Emulator are bundled) or the standalone [SDK command-line tools](https://developer.android.com/studio#command-tools) |
| **Internet connection** | Downloads Python, frida-server, and the system image if any are missing |

> **WSL2 users**: see the [WSL2 port bridge](#wsl2-users-one-extra-step) section before running.

**What's automated:**
- **Python** — downloaded automatically as a portable binary if not on your system
- **Android system image** — downloaded automatically (~1.3 GB, one-time) if not already installed; you must accept the Android SDK License Agreement
- **Emulator** — a temporary `wvd_extractor_tmp` AVD is created, booted, used, then deleted

The script looks for the SDK in the standard locations (`%LOCALAPPDATA%\Android\Sdk` on Windows / `/mnt/c/Users/<user>/AppData/Local/Android/Sdk` from WSL2 / `~/Android/Sdk` on Linux).

> **Why API 29 Google APIs?** The script uses Android 10 (API 29) with the `google_apis` image — not `google_play`. The `google_play` variant blocks `adb root` and `su`, which frida requires to hook into Widevine. API 29 is the sweet spot: modern Widevine L3 support with reliable emulation.

### Option B: Physical Android Device (Rooted)

| Requirement | Details |
|---|---|
| **Rooted device** | Via Magisk or similar |
| **USB debugging** | Settings → Developer Options → USB Debugging ON |
| **USB cable** | Connect to your computer |
| **Internet connection** | To download Python (if missing) and frida-server |

---

## Quick Start

### Linux / WSL2

```bash
cd wvd-extractor

# 1. Install dependencies (one time)
chmod +x setup.sh extract.sh
./setup.sh

# 2. Run — the emulator is created and started automatically if the SDK is found
./extract.sh
```

### Windows (PowerShell)

```powershell
cd wvd-extractor

# 1. Install dependencies (one time)
.\setup.ps1

# 2. Run — the emulator is created and started automatically if the SDK is found
.\extract.ps1
```

### Options

```
./extract.sh                        # Auto-detect or auto-create device
./extract.sh --device emulator-5554 # Use a specific already-running device
./extract.sh --no-create            # Skip emulator auto-create, use existing device
./extract.sh --keep-avd             # Keep the temporary AVD after extraction
./extract.sh --timeout 300          # Increase KeyDive timeout (default: 180s)
./extract.sh --output /tmp/cdm      # Custom output directory
```

---

## What Happens Under the Hood

1. **Environment detection** — figures out if you're on Linux, WSL2, or Windows
2. **Prerequisite checks** — verifies ADB is available, sets up WSL2↔Windows bridge if needed
3. **Emulator auto-create** — if no device is connected, finds your Android SDK, writes a temporary AVD config, and launches the emulator via PowerShell (WSL2) or directly (Linux/Windows)
4. **Device connection** — waits for the emulator to boot, then gets root access
5. **frida-server** — downloads the right version for your device architecture, pushes and starts it
6. **KeyDive** — hooks into the Widevine CDM, triggers a DRM test, extracts keys
7. **Install** — verifies the `.wvd` file and lets you choose where to save it

---

## WSL2 Users: One Extra Step

The Android emulator runs as a Windows process. For WSL2's ADB to see it, you need to forward port 5037 **once** (run in a **Windows PowerShell as Administrator**):

```powershell
netsh interface portproxy add v4tov4 listenport=5037 listenaddress=0.0.0.0 connectport=5037 connectaddress=127.0.0.1
```

The script will print this exact command and exit if the bridge isn't active. To make it permanent, add it to a startup task or run it whenever you reboot Windows.

> Verify with `adb devices` in a Windows terminal — the emulator should appear there after it boots.

---

## Troubleshooting

### "Android SDK not found — cannot auto-create emulator"

- Install [Android Studio](https://developer.android.com/studio); the SDK is bundled at `%LOCALAPPDATA%\Android\Sdk`
- Or set the `ANDROID_HOME` environment variable to your SDK path
- The emulator binary itself must be present — install it via SDK Manager → SDK Tools → Android Emulator

### "No compatible system image found" / system image download fails

The script downloads the system image automatically. If the download fails:
- Check your internet connection
- Install manually: Android Studio → **SDK Manager** → **SDK Platforms** → check **Show Package Details** → **Android 10.0 (API 29) → Google APIs Intel x86_64 Atom System Image → Install**
- The script also accepts: API 29 x86, API 28 x86_64/x86, API 33 x86_64

### "No Android devices found"

- **Emulator**: if auto-create failed, check the troubleshooting steps above; or start one manually in Android Studio
- **Physical device**: enable USB debugging, reconnect cable, check `adb devices`
- **WSL2**: set up the port bridge (see section above)

### "Could not get root access"

- **Emulator**: the auto-created AVD uses a "Google APIs" image (not "Google Play") so root always works
- **Physical device**: make sure it's properly rooted (check with `adb shell su`)
- If you created the emulator manually, ensure you chose **"Google APIs"**, not **"Google Play"**

### "KeyDive timed out"

- The emulator can be slow to start on the first boot. Increase the timeout:
  ```
  ./extract.sh --timeout 300
  ```
- Make sure the emulator has internet access (try opening a website in Chrome inside it)

### "frida-server download failed"

- Check your internet connection
- If behind a proxy, set `http_proxy` / `https_proxy` environment variables

### "No .wvd file found"

- KeyDive ran but couldn't extract the CDM
- Try restarting the emulator and running again
- Try a different API level in the SDK Manager and re-run

---

## Cleanup

After extraction, the emulator and AVD are deleted automatically. To free up all space:

```bash
# Delete everything (venv, portable Python, cached frida-server)
rm -rf /path/to/wvd-extractor
rm -rf ~/.cache/wvd-extractor
```

The Android system image (~1.4 GB) stays in your SDK directory — it's part of your Android SDK installation and can be removed via Android Studio → SDK Manager.

---

## File Structure

```
wvd-extractor/
├── setup.sh / setup.ps1       ← Install dependencies (auto-downloads Python if needed)
├── extract.sh / extract.ps1   ← Run extraction
├── requirements.txt            ← Python packages
├── .python/                    ← Portable Python (created if none found on system)
├── venv-wvd/                   ← Python virtual environment (created by setup)
├── cdm-output/                 ← Where extracted files go
└── src/
    ├── main.py                 ← Main orchestrator (7-step flow)
    ├── avd_manager.py          ← Emulator auto-create, system image download & lifecycle
    ├── env_detect.py           ← Platform detection (Linux / WSL2 / Windows)
    ├── check_prereqs.py        ← Prerequisite validation
    ├── adb_utils.py            ← ADB device management
    ├── frida_setup.py          ← frida-server lifecycle
    ├── keydive_runner.py       ← KeyDive execution
    ├── wvd_install.py          ← WVD verification & install
    └── ui.py                   ← Terminal output formatting
```
