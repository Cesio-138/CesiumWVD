<h1 align="center">CesiumWVD</h1>

<p align="center">
  Automated Widevine CDM extraction from Android devices and emulators.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20WSL2%20%7C%20Windows-brightgreen" alt="Platform">
  <img src="https://img.shields.io/badge/python-%E2%89%A53.8-3776AB" alt="Python 3.8+">
</p>

---

Extract a Widevine CDM (`device.wvd`) in minutes. This is a **one-time process** — once you have the file, use it with [pywidevine](https://github.com/devine-dl/pywidevine) and never run this again.

> [!IMPORTANT]
> **macOS is not supported.** Linux, WSL2, and Windows only.

## Disclaimer

This tool is provided for **personal, educational, and research purposes only**. Extracting Widevine CDM keys may violate the Terms of Service of certain platforms. The authors are not responsible for any misuse. **You are solely responsible for compliance with applicable laws and service agreements.**

## Get Started

Download the latest release for your platform from the **[Releases page](../../releases/latest)**:

| Platform | Download |
|---|---|
| **Linux** | `CesiumWVD-x.x.x.AppImage` — make executable, double-click to run |
| **Windows** | `CesiumWVD-Setup-x.x.x.exe` — run the installer, launch from the desktop shortcut |

Open CesiumWVD. The wizard guides you through four automatic steps:

1. **Environment check** — detects your Android SDK and ADB. If anything is missing, it shows a direct install link and a Re-check button.
2. **Device setup** — auto-creates a temporary Android emulator, or uses a connected rooted phone.
3. **CDM extraction** — deploys frida-server, runs KeyDive, and captures the Widevine keys.
4. **Save** — verifies the `.wvd` file and lets you choose where to keep it.

**The whole process takes about 3–5 minutes.**

### What you need

| | |
|---|---|
| **Android SDK** | Install [Android Studio](https://developer.android.com/studio) — it includes the SDK and emulator |

> **WSL2 users:** a one-time network bridge step is required before the emulator is reachable. [See WSL2 Setup →](docs/troubleshooting.md#wsl2-setup)

## CLI / Headless Use

CesiumWVD also runs as a command-line tool — useful for automation or headless environments:

```bash
./setup.sh && ./extract.sh        # Linux / WSL2
.\setup.ps1; .\extract.ps1        # Windows PowerShell
```

[Full CLI guide →](docs/cli.md)

## Documentation

| | |
|---|---|
| [GUI Guide](docs/gui.md) | Building from source, development mode |
| [CLI Guide](docs/cli.md) | Options, flags, scripting, WSL2 bridge |
| [Architecture](docs/architecture.md) | IPC protocol and pipeline internals |
| [Troubleshooting](docs/troubleshooting.md) | Error messages and fixes |

## Related Projects

- [KeyDive](https://github.com/hyugogirubato/KeyDive) — Widevine L3 key extraction via frida hooking
- [pywidevine](https://github.com/devine-dl/pywidevine) — Python Widevine CDM implementation
- [frida](https://frida.re/) — Dynamic instrumentation toolkit

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
