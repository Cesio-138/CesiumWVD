"""
Verify the extracted .wvd and install it to the user's chosen location.
"""

import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from . import env_detect
from .ui import error, info, prompt_choice, prompt_path, success


def verify_wvd(wvd_path: Path) -> bool:
    """Load the .wvd with pywidevine and print device info. Returns True if valid."""
    # Basic file check
    if not wvd_path.exists():
        error("WVD file not found.")
        return False
    size = wvd_path.stat().st_size
    if size < 100:
        error(f"WVD file is suspiciously small ({size} bytes).")
        return False

    # Try pywidevine for detailed verification (optional dependency)
    try:
        from pywidevine.device import Device
        d = Device.load(str(wvd_path))
        success("WVD file is valid!")
        info(f"  Type: {d.type.name}")
        info(f"  Security Level: {d.security_level}")
        info(f"  System ID: {d.system_id}")
        return True
    except ImportError:
        success(f"WVD file created ({size:,} bytes).")
        info("Install 'pywidevine' for detailed verification: pip install pywidevine")
        return True
    except Exception as e:
        error(f"WVD file appears invalid: {e}")
        return False


def _get_install_options() -> List[Tuple[str, Optional[Path]]]:
    """Build the list of install destinations based on the platform."""
    cesio_dir = env_detect.get_cesio_data_dir()
    options = []

    label = "Cesio app data"
    if env_detect.is_windows():
        label += f" ({cesio_dir})"
    else:
        label += f" ({cesio_dir})"
    options.append((label, cesio_dir / "device.wvd"))

    options.append(("Current directory (./device.wvd)", Path.cwd() / "device.wvd"))
    options.append(("Custom path...", None))

    return options


def install_wvd(wvd_path: Path):
    """
    Interactive prompt asking the user where to install the .wvd file.
    Copies to the selected destination.
    """
    options = _get_install_options()
    labels = [opt[0] for opt in options]

    choice = prompt_choice("Where should the WVD file be installed?", labels, default=1)
    _, dest = options[choice - 1]

    if dest is None:
        raw = prompt_path("Enter the full destination path (file, not directory)")
        dest = Path(raw).expanduser().resolve()

    # Ensure parent directory exists
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Copy
    shutil.copy2(str(wvd_path), str(dest))
    success(f"Installed: {dest}")

    # Offer to copy to additional locations
    from .ui import confirm
    if confirm("Copy to another location as well?", default=False):
        install_wvd(wvd_path)
