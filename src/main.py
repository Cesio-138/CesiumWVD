#!/usr/bin/env python3
"""
WVD Extractor — automated Widevine CDM extraction.

Orchestrates the full pipeline:
  1. Detect environment (Linux / WSL2 / Windows)
  2. Check prerequisites (Python, ADB, WSL2 bridge)
  3. Set up Android emulator (auto-create or use existing device)
  4. Connect to device and get root
  5. Set up frida-server on device
  6. Run KeyDive to extract CDM
  7. Verify and install the .wvd file
"""

import argparse
import sys
from pathlib import Path

# Ensure src/ is importable when run directly
_here = Path(__file__).resolve().parent
if str(_here.parent) not in sys.path:
    sys.path.insert(0, str(_here.parent))

from src import (  # noqa: E402
    adb_utils,
    avd_manager,
    check_prereqs,
    env_detect,
    frida_setup,
    keydive_runner,
    wvd_install,
)
from src.ui import error, fatal, info, step, success  # noqa: E402

TOTAL_STEPS = 7
OUTPUT_DIR = _here.parent / "cdm-output"


def banner():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║        WVD Extractor — Cesio-138             ║")
    print("  ║  Automated Widevine CDM extraction tool      ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()


def parse_args():
    p = argparse.ArgumentParser(
        description="Extract a Widevine CDM (device.wvd) from an Android device.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python src/main.py                   Auto-detect device
  python src/main.py --device emu-5554 Use a specific device
  python src/main.py --timeout 300     Increase KeyDive timeout
""",
    )
    p.add_argument(
        "-d", "--device",
        metavar="SERIAL",
        help="ADB serial of the target device (skip emulator auto-create)",
    )
    p.add_argument(
        "--no-create",
        action="store_true",
        help="Skip emulator auto-create, use already-running device",
    )
    p.add_argument(
        "--keep-avd",
        action="store_true",
        help="Keep the temporary AVD after extraction (don't delete it)",
    )
    p.add_argument(
        "-t", "--timeout",
        type=int,
        default=180,
        metavar="SECS",
        help="KeyDive timeout in seconds (default: 180)",
    )
    p.add_argument(
        "-o", "--output",
        type=Path,
        default=OUTPUT_DIR,
        metavar="DIR",
        help=f"Directory for CDM output files (default: {OUTPUT_DIR})",
    )
    return p.parse_args()


def main():
    banner()
    args = parse_args()

    # ── Step 1: Environment Detection ─────────────────────────────────────
    step(1, TOTAL_STEPS, "Detecting environment")
    platform = env_detect.get_platform_label()
    success(f"Platform: {platform}")
    if env_detect.is_wsl2():
        info("WSL2 mode: will bridge ADB to the Windows host automatically.")

    # ── Step 2: Prerequisites ─────────────────────────────────────────────
    step(2, TOTAL_STEPS, "Checking prerequisites")
    adb = check_prereqs.run_all_checks()
    success("All prerequisites met.")

    # ── Step 3: Emulator Setup ───────────────────────────────────────────
    step(3, TOTAL_STEPS, "Setting up Android emulator")
    auto_created_serial = None
    serial = None

    if args.device:
        # User explicitly specified a device — skip auto-create
        info(f"Using specified device: {args.device}")
        serial = args.device
    else:
        devices = adb_utils.list_devices(adb)
        online = [d for d in devices if d.is_online]

        if online and args.no_create:
            info(f"Found {len(online)} device(s) already running.")
        elif online:
            # Devices already connected — ask user
            from src.ui import prompt_choice
            choice = prompt_choice(
                f"{len(online)} device(s) already connected. What would you like to do?",
                [
                    f"Use existing: {online[0].serial}" if len(online) == 1
                    else f"Select from {len(online)} devices",
                    "Create a new temporary emulator instead",
                ],
                default=1,
            )
            if choice == 2:
                online = []  # fall through to auto-create

        if not online:
            # Try auto-create
            available, reason = avd_manager.is_available()
            if available:
                info("No device connected — creating a temporary Android emulator...")
                auto_created_serial = avd_manager.setup_emulator(adb)
                if not auto_created_serial:
                    fatal("Failed to start emulator automatically.")
                    info("Start an emulator manually in Android Studio, then re-run.")
                    sys.exit(1)
                serial = auto_created_serial
            else:
                error(f"Cannot auto-create emulator: {reason}")
                info("Please start an Android emulator manually in Android Studio,")
                info("then re-run this script.")
                sys.exit(1)

    # ── Step 4: Device Connection & Root ──────────────────────────────────
    step(4, TOTAL_STEPS, "Connecting to Android device")
    serial = adb_utils.select_device(adb, forced_serial=serial)
    if not adb_utils.root_device(adb, serial):
        fatal("Root access is required. See README for help.")
        sys.exit(1)

    # ── Step 5: Frida Server ──────────────────────────────────────────────
    step(5, TOTAL_STEPS, "Setting up frida-server")
    frida_setup.ensure_frida_server(adb, serial)

    # Dismiss Chrome's first-run dialog so the DRM test page can load
    adb_utils.dismiss_chrome_first_run(adb, serial)

    # ── Step 6: KeyDive Extraction ────────────────────────────────────────
    step(6, TOTAL_STEPS, "Extracting Widevine CDM (this may take a minute)")
    wvd_path = keydive_runner.run_keydive(serial, args.output, timeout=args.timeout)
    if not wvd_path:
        fatal("CDM extraction failed. Check the output above for details.")
        info("Common fixes:")
        info("  • Make sure the emulator has internet access")
        info("  • Try a different API level (29 recommended)")
        info("  • Increase timeout with --timeout 300")
        # Clean up AVD if we created it
        if auto_created_serial and not args.keep_avd:
            info("Cleaning up temporary emulator...")
            avd_manager.kill_emulator(adb, auto_created_serial)
            avd_manager.delete_avd()
        sys.exit(1)

    # ── Step 7: Verify & Install ──────────────────────────────────────────
    step(7, TOTAL_STEPS, "Verifying and installing WVD file")
    if not wvd_install.verify_wvd(wvd_path):
        fatal("The extracted WVD file could not be verified.")
        info(f"Raw file location: {wvd_path}")
        sys.exit(1)

    wvd_install.install_wvd(wvd_path)

    # ── Cleanup auto-created emulator ────────────────────────────────────
    if auto_created_serial:
        print()
        if args.keep_avd:
            info("Keeping temporary emulator (--keep-avd was set).")
        else:
            from src.ui import confirm
            if confirm("Shut down and delete the temporary emulator?", default=True):
                info("Shutting down emulator...")
                avd_manager.kill_emulator(adb, auto_created_serial)
                avd_manager.delete_avd()

    # ── Done ──────────────────────────────────────────────────────────────
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║             All done! 🎉                     ║")
    print("  ║  Your device.wvd is ready to use.            ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(130)
