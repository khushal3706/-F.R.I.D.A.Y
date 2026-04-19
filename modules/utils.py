"""
╔══════════════════════════════════════════════════════════════╗
║      FRIDAY — Clipboard & File Utils (modules/utils.py)     ║
║  Clipboard access, file read/write, and notification toast  ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from core.logger import get_logger

log = get_logger("Utils")


# ─────────────────────────────────────────────────────────────
# ▸ CLIPBOARD
# ─────────────────────────────────────────────────────────────
def get_clipboard() -> str:
    """
    Return the current clipboard text contents.
    Requires: pip install pyperclip
    """
    try:
        import pyperclip
        text = pyperclip.paste()
        log.debug(f"Clipboard read ({len(text)} chars).")
        return text
    except ImportError:
        log.error("pyperclip not installed.  Run: pip install pyperclip")
        return ""


def set_clipboard(text: str):
    """
    Write a string to the system clipboard.
    Requires: pip install pyperclip
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        log.info(f"Clipboard set ({len(text)} chars).")
    except ImportError:
        log.error("pyperclip not installed.  Run: pip install pyperclip")


# ─────────────────────────────────────────────────────────────
# ▸ FILE HELPERS
# ─────────────────────────────────────────────────────────────
def read_file(path: str | Path, encoding: str = "utf-8") -> str:
    """Read a text file and return its contents as a string."""
    p = Path(path)
    if not p.exists():
        log.error(f"File not found: {p}")
        return ""
    text = p.read_text(encoding=encoding)
    log.debug(f"Read {len(text)} chars from {p}")
    return text


def write_file(path: str | Path, content: str, encoding: str = "utf-8", append: bool = False):
    """
    Write or append a string to a file (creates parent dirs if needed).

    Args:
        path    : Target file path.
        content : Text to write.
        append  : If True, append instead of overwrite.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(p, mode, encoding=encoding) as f:
        f.write(content)
    log.info(f"{'Appended' if append else 'Wrote'} {len(content)} chars to {p}")


def read_json(path: str | Path) -> dict | list:
    """Read and parse a JSON file."""
    text = read_file(path)
    if not text:
        return {}
    return json.loads(text)


def write_json(path: str | Path, data: dict | list, indent: int = 2):
    """Serialise `data` to a pretty-printed JSON file."""
    write_file(path, json.dumps(data, indent=indent, ensure_ascii=False))


def list_files(directory: str | Path, pattern: str = "*") -> list[Path]:
    """
    Return a sorted list of files matching a glob pattern.

    Args:
        directory : Directory to search.
        pattern   : Glob pattern (e.g. '*.txt', '**/*.py').

    Returns:
        List of Path objects.
    """
    d = Path(directory)
    if not d.is_dir():
        log.warning(f"Not a directory: {d}")
        return []
    files = sorted(d.glob(pattern))
    log.debug(f"Found {len(files)} file(s) in {d} matching '{pattern}'")
    return files


def safe_copy(src: str | Path, dst: str | Path) -> bool:
    """Copy a file, creating destination parent directories as needed."""
    s, d = Path(src), Path(dst)
    d.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(str(s), str(d))
        log.info(f"Copied {s} → {d}")
        return True
    except Exception as exc:
        log.error(f"Copy failed: {exc}")
        return False


# ─────────────────────────────────────────────────────────────
# ▸ WINDOWS TOAST NOTIFICATIONS
# ─────────────────────────────────────────────────────────────
def notify(title: str, message: str, duration: int = 5):
    """
    Show a Windows desktop toast notification.

    Requires: pip install win10toast
    Falls back to a print statement if unavailable.

    Args:
        title    : Notification title.
        message  : Notification body text.
        duration : Seconds the toast stays visible.
    """
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=duration, threaded=True)
        log.info(f"Notification sent: {title!r}")
    except ImportError:
        log.warning("win10toast not installed — printing notification instead.")
        print(f"\n🔔  [{title}] {message}\n")
    except Exception as exc:
        log.error(f"Notification failed: {exc}")
        print(f"\n🔔  [{title}] {message}\n")


# ─────────────────────────────────────────────────────────────
# ▸ TIMESTAMP / FORMATTING
# ─────────────────────────────────────────────────────────────
def timestamp(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Return the current local datetime as a formatted string."""
    return datetime.now().strftime(fmt)


def human_size(n_bytes: int) -> str:
    """Convert byte count to a human-readable string (KB / MB / GB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} PB"


# ─────────────────────────────────────────────────────────────
# ▸ ENVIRONMENT HELPERS
# ─────────────────────────────────────────────────────────────
def load_dotenv(path: str = ".env"):
    """
    Manually load KEY=VALUE pairs from a .env file into os.environ.
    This avoids requiring the python-dotenv package.
    """
    p = Path(path)
    if not p.exists():
        log.debug(".env file not found — skipping.")
        return
    loaded = 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)
        loaded += 1
    log.info(f"Loaded {loaded} variable(s) from {p}")
