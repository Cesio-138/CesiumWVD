# Troubleshooting

Detailed solutions for common CesiumWVD issues.

## WSL2 Setup

The Android emulator runs as a Windows process. WSL2 cannot reach it by default — you need to forward ADB port 5037 **once**.

Run in a **Windows PowerShell as Administrator**:

```powershell
netsh interface portproxy add v4tov4 listenport=5037 listenaddress=0.0.0.0 connectport=5037 connectaddress=127.0.0.1
```

CesiumWVD detects whether the bridge is active and prints this command with instructions if it isn't. To make it permanent, add it to a Windows startup task.

Verify with `adb devices` in a Windows terminal — the emulator should appear after it boots.

## "Android SDK not found — cannot auto-create emulator"

CesiumWVD looks for the Android SDK in these locations:

| Platform | Default path |
|----------|-------------|
| Linux | `~/Android/Sdk` |
| WSL2 | `/mnt/c/Users/<user>/AppData/Local/Android/Sdk` |
| Windows | `%LOCALAPPDATA%\Android\Sdk` |

If your SDK is elsewhere, set the `ANDROID_HOME` environment variable:

```bash
# Linux / WSL2
export ANDROID_HOME=/path/to/your/Sdk

# Windows PowerShell
$env:ANDROID_HOME = "C:\path\to\your\Sdk"
```

**Verify:** the directory must contain `platform-tools/adb` and `emulator/emulator`.

If you don't have the SDK at all, install [Android Studio](https://developer.android.com/studio) (includes SDK + Emulator) or the standalone [SDK command-line tools](https://developer.android.com/studio#command-tools).

## "No compatible system image found" / system image download fails

CesiumWVD needs the `google_apis` system image for API 29. The script downloads it automatically, but if that fails:

### Manual install

```bash
# Using sdkmanager (from Android SDK command-line tools)
sdkmanager "system-images;android-29;google_apis;x86_64"
```

### Common causes

- **Proxy/firewall** blocking `dl.google.com`
- **Disk space** — the image is ~1.4 GB
- **Wrong image type** — must be `google_apis`, NOT `google_play` (the Play Store image blocks root access)

### Verify

```bash
ls "$ANDROID_HOME/system-images/android-29/google_apis/x86_64/"
# Should contain system.img, vendor.img, etc.
```

## "No Android devices found"

### Emulator mode

1. Check that the Android SDK was found (see above)
2. Verify the emulator started: look for an emulator window or run `adb devices`
3. If using `--no-create`, make sure a device is already running

### Physical device

1. Enable **USB Debugging**: Settings → Developer Options → USB Debugging ON
2. Connect via USB and approve the debugging prompt on the phone
3. Run `adb devices` — the device should appear as `device` (not `unauthorized`)

### WSL2

1. Ensure the [port bridge](../README.md#wsl2-users-one-extra-step) is set up
2. The ADB server must be running on the **Windows side**: open a Windows terminal and run `adb start-server`
3. From WSL2, `adb devices` should list the same devices as the Windows side

## "Could not get root access"

Root access is **required** for frida to hook into the Widevine CDM.

### Emulator

- You **must** use the `google_apis` system image (not `google_play`)
- The `google_play` variant ships with a locked-down `adbd` that rejects `adb root`
- CesiumWVD auto-creates emulators with the correct image; this error usually means you're pointing at an existing emulator with the wrong image

### Physical device

- The device must be rooted (e.g., via [Magisk](https://github.com/topjohnwu/Magisk))
- Grant root access when the Magisk prompt appears after running `adb root`
- If `adb root` says "adbd cannot run as root in production builds", root is not properly set up

## "KeyDive timed out"

KeyDive needs to hook into the Widevine CDM while a DRM operation is in progress. The default timeout is 180 seconds.

### Solutions

1. **Increase the timeout**:
   ```bash
   ./extract.sh --timeout 300
   ```

2. **Restart and retry** — sometimes the emulator needs a cold start:
   ```bash
   # If using auto-create, just re-run:
   ./extract.sh
   ```

3. **Check the emulator** is responsive: open a shell with `adb shell` and verify it responds

4. **Slow machines** — emulators on machines without hardware virtualization (KVM on Linux, HAXM/Hyper-V on Windows) will be much slower. Enable KVM:
   ```bash
   # Check KVM support
   egrep -c '(vmx|svm)' /proc/cpuinfo   # Should be > 0
   ls /dev/kvm                            # Should exist
   ```

## "frida-server download failed"

CesiumWVD downloads frida-server from GitHub Releases. Failures are usually network-related.

### Manual download

1. Find your frida version:
   ```bash
   source venv-wvd/bin/activate
   python -c "import frida; print(frida.__version__)"
   ```

2. Find your device architecture:
   ```bash
   adb shell getprop ro.product.cpu.abi
   # Usually: x86_64 (emulator) or arm64-v8a (physical)
   ```

3. Download from: `https://github.com/frida/frida/releases/download/<version>/frida-server-<version>-android-<arch>.xz`

4. Extract and place the binary at:
   ```
   ~/.cache/CesiumWVD/frida-server-<version>-android-<arch>
   ```
   (no file extension — the bare binary)

### Common causes

- **GitHub rate limits** — try again later or use a VPN
- **Corporate proxy/firewall** blocking GitHub
- **Disk permission** on `~/.cache/`

## "No .wvd file found"

The KeyDive session completed but no `.wvd` file was produced.

### Common causes

1. **Timeout too short** — the DRM trigger may not have fired before KeyDive gave up. Increase with `--timeout 300`.

2. **DRM trigger failed** — the frida script that provokes a Widevine key request may have encountered an error. Check the log output for `[frida]` messages.

3. **Incompatible system image** — ensure you're using Android 10 (API 29) with `google_apis`. Other API levels may have a different Widevine CDM that KeyDive can't hook.

4. **KeyDive version mismatch** — ensure `keydive >= 3.0.0` is installed:
   ```bash
   source venv-wvd/bin/activate
   pip show keydive
   ```

### Recovery

Re-run the extraction. The emulator and frida-server setup are cached, so subsequent runs are much faster.
