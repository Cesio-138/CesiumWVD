"""
Pretty terminal output helpers.

When _ipc_mode is True (set by ipc_bridge.py), all output is emitted as JSON
lines to stdout instead of ANSI-colored text, and prompts block on stdin for
a JSON response.
"""

import json
import sys
import threading
from typing import List, Optional

# ─── IPC mode ─────────────────────────────────────────────────────────────────
_ipc_mode = False
_ipc_lock = threading.Lock()
_prompt_id_counter = 0


def enable_ipc_mode():
    global _ipc_mode
    _ipc_mode = True


def _emit(obj: dict):
    """Write a JSON line to stdout (thread-safe)."""
    with _ipc_lock:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def _wait_response() -> dict:
    """Block until one JSON line arrives on stdin."""
    line = sys.stdin.readline()
    if not line:
        raise EOFError("stdin closed")
    return json.loads(line.strip())


def _next_prompt_id() -> str:
    global _prompt_id_counter
    _prompt_id_counter += 1
    return f"prompt_{_prompt_id_counter}"


# ─── ANSI colors (disabled on non-tty or Windows without VT) ─────────────────
_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_RESET = "\033[0m" if _COLOR else ""
_BOLD = "\033[1m" if _COLOR else ""
_GREEN = "\033[92m" if _COLOR else ""
_YELLOW = "\033[93m" if _COLOR else ""
_RED = "\033[91m" if _COLOR else ""
_CYAN = "\033[96m" if _COLOR else ""
_DIM = "\033[2m" if _COLOR else ""


# ─── Output functions ─────────────────────────────────────────────────────────

def step(number: int, total: int, message: str):
    """Print a numbered step header."""
    if _ipc_mode:
        _emit({"event": "step", "step": number, "total": total, "title": message})
        return
    print(f"\n{_BOLD}{_CYAN}[{number}/{total}]{_RESET} {_BOLD}{message}{_RESET}")


def info(message: str):
    if _ipc_mode:
        _emit({"event": "info", "message": message})
        return
    print(f"  {_DIM}→{_RESET} {message}")


def success(message: str):
    if _ipc_mode:
        _emit({"event": "success", "message": message})
        return
    print(f"  {_GREEN}✓{_RESET} {message}")


def warn(message: str):
    if _ipc_mode:
        _emit({"event": "warn", "message": message})
        return
    print(f"  {_YELLOW}⚠{_RESET} {message}")


def error(message: str):
    if _ipc_mode:
        _emit({"event": "error", "message": message})
        return
    print(f"  {_RED}✗{_RESET} {message}")


def fatal(message: str):
    if _ipc_mode:
        _emit({"event": "fatal", "message": message})
        return
    print(f"\n{_RED}{_BOLD}ERROR:{_RESET} {message}")


def log(message: str):
    """Log line (e.g. keydive output). In terminal mode, just prints."""
    if _ipc_mode:
        _emit({"event": "log", "message": message})
        return
    print(message, end="")


def progress(percent: int, label: str = ""):
    """Progress update (only meaningful in IPC mode)."""
    if _ipc_mode:
        _emit({"event": "progress", "percent": percent, "label": label})


def command_block(command: str, description: str = ""):
    """Emit a command the user should run. In IPC mode sends a structured event;
    in terminal mode prints it with formatting."""
    if _ipc_mode:
        _emit({"event": "command_block", "command": command, "description": description})
        return
    if description:
        print(f"\n  {_CYAN}# {description}{_RESET}")
    print(f"\n  {_BOLD}{_CYAN}  {command}{_RESET}\n")


# ─── Interactive prompts ──────────────────────────────────────────────────────

def prompt_choice(question: str, options: List[str], default: int = 1) -> int:
    """
    Show a numbered menu and return the 1-based index of the user's choice.
    """
    if _ipc_mode:
        pid = _next_prompt_id()
        _emit({
            "event": "prompt_choice",
            "id": pid,
            "question": question,
            "options": options,
            "default": default,
        })
        resp = _wait_response()
        val = resp.get("value", default)
        return int(val) if isinstance(val, (int, str)) else default

    print(f"\n  {_BOLD}{question}{_RESET}")
    for i, opt in enumerate(options, 1):
        tag = f" {_GREEN}(recommended){_RESET}" if i == default else ""
        print(f"    [{i}] {opt}{tag}")

    while True:
        try:
            raw = input(f"\n  Enter choice [1-{len(options)}] (default {default}): ").strip()
            if not raw:
                return default
            choice = int(raw)
            if 1 <= choice <= len(options):
                return choice
        except (ValueError, EOFError):
            pass
        error(f"Please enter a number between 1 and {len(options)}.")


def prompt_path(message: str) -> str:
    """Ask the user for a file path."""
    if _ipc_mode:
        pid = _next_prompt_id()
        _emit({"event": "prompt_path", "id": pid, "question": message})
        resp = _wait_response()
        return str(resp.get("value", ""))

    while True:
        try:
            raw = input(f"  {message}: ").strip()
            if raw:
                return raw
        except EOFError:
            pass
        error("Please enter a valid path.")


def confirm(question: str, default: bool = True) -> bool:
    """Yes/no confirmation prompt."""
    if _ipc_mode:
        pid = _next_prompt_id()
        _emit({
            "event": "prompt_confirm",
            "id": pid,
            "question": question,
            "default": default,
        })
        resp = _wait_response()
        val = resp.get("value", default)
        return bool(val) if isinstance(val, bool) else str(val).lower() in ("true", "y", "yes", "1")

    hint = "Y/n" if default else "y/N"
    try:
        raw = input(f"  {question} [{hint}]: ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw in ("y", "yes")
