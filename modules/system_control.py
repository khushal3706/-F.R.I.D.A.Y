"""
╔══════════════════════════════════════════════════════════════╗
║     FRIDAY — System Control (modules/system_control.py)     ║
║  Mouse, keyboard, window management, and app launching      ║
╚══════════════════════════════════════════════════════════════╝
"""

import time
import subprocess
import pyautogui
import pygetwindow as gw
from core.logger import get_logger
from core.safety import is_killed
from config import PYAUTOGUI_PAUSE

log = get_logger("SystemControl")

# Apply global PyAutoGUI timing pause (safety buffer between actions)
pyautogui.PAUSE = PYAUTOGUI_PAUSE


# ─────────────────────────────────────────────────────────────
# ▸ GUARD DECORATOR — aborts any action if kill-switch is set
# ─────────────────────────────────────────────────────────────
def _safe(fn):
    """Decorator: skips execution if the kill-switch has fired."""
    def wrapper(*args, **kwargs):
        if is_killed():
            log.warning(f"Kill-switch active — skipping {fn.__name__}()")
            return None
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# ─────────────────────────────────────────────────────────────
# ▸ MOUSE CONTROLS
# ─────────────────────────────────────────────────────────────
@_safe
def click(x: int, y: int, button: str = "left", clicks: int = 1, delay: float = 0.1):
    """
    Click at absolute screen coordinates.

    Args:
        x, y    : Screen pixel coordinates.
        button  : 'left' | 'right' | 'middle'
        clicks  : Number of clicks (2 = double-click).
        delay   : Seconds to wait after clicking.
    """
    log.info(f"Click [{button}] @ ({x}, {y})  ×{clicks}")
    pyautogui.click(x, y, button=button, clicks=clicks)
    time.sleep(delay)


@_safe
def move_to(x: int, y: int, duration: float = 0.4):
    """Smoothly move the mouse cursor to (x, y)."""
    log.debug(f"Moving mouse to ({x}, {y})")
    pyautogui.moveTo(x, y, duration=duration)


@_safe
def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
    """Click-drag from (x1, y1) to (x2, y2)."""
    log.info(f"Drag  ({x1},{y1}) → ({x2},{y2})")
    pyautogui.moveTo(x1, y1)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")


@_safe
def scroll(x: int, y: int, amount: int = 3, direction: str = "down"):
    """
    Scroll the mouse wheel at a given position.

    Args:
        amount    : Number of scroll 'clicks'.
        direction : 'up' | 'down'
    """
    clicks = amount if direction == "up" else -amount
    log.debug(f"Scroll {direction} ×{amount} @ ({x},{y})")
    pyautogui.scroll(clicks, x=x, y=y)


# ─────────────────────────────────────────────────────────────
# ▸ KEYBOARD CONTROLS
# ─────────────────────────────────────────────────────────────
@_safe
def type_text(text: str, interval: float = 0.05):
    """
    Type a string of text with a per-character interval.

    Args:
        text     : The string to type.
        interval : Seconds between each keypress.
    """
    log.info(f"Typing: {text[:60]}{'...' if len(text) > 60 else ''}")
    pyautogui.typewrite(text, interval=interval)


@_safe
def press_key(*keys: str):
    """
    Press one or more keys (hotkey if multiple).

    Examples:
        press_key('enter')
        press_key('ctrl', 'c')
        press_key('alt', 'F4')
    """
    log.info(f"Key press: {' + '.join(keys)}")
    if len(keys) == 1:
        pyautogui.press(keys[0])
    else:
        pyautogui.hotkey(*keys)


@_safe
def hold_key(key: str, duration: float = 0.5):
    """Hold a key down for `duration` seconds then release."""
    log.debug(f"Holding key '{key}' for {duration}s")
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)


# ─────────────────────────────────────────────────────────────
# ▸ WINDOW MANAGEMENT
# ─────────────────────────────────────────────────────────────
def list_windows() -> list[str]:
    """Return titles of all currently visible windows."""
    titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
    log.debug(f"Open windows ({len(titles)}): {titles}")
    return titles


def focus_window(title_fragment: str) -> bool:
    """
    Bring a window whose title contains `title_fragment` to the foreground.

    Args:
        title_fragment : Case-insensitive substring to match.

    Returns:
        True if a matching window was found and focused.
    """
    matches = [w for w in gw.getAllWindows()
               if title_fragment.lower() in w.title.lower() and w.title.strip()]
    if not matches:
        log.warning(f"No window found matching '{title_fragment}'")
        return False
    win = matches[0]
    log.info(f"Focusing window: '{win.title}'")
    try:
        win.activate()
        time.sleep(0.5)   # let the window paint
        return True
    except Exception as exc:
        log.error(f"Could not activate window '{win.title}': {exc}")
        return False


def minimize_window(title_fragment: str):
    """Minimise the first window matching `title_fragment`."""
    for win in gw.getAllWindows():
        if title_fragment.lower() in win.title.lower():
            win.minimize()
            log.info(f"Minimized: {win.title}")
            return
    log.warning(f"No window to minimise matching '{title_fragment}'")


def close_window(title_fragment: str):
    """Close the first window matching `title_fragment`."""
    for win in gw.getAllWindows():
        if title_fragment.lower() in win.title.lower():
            win.close()
            log.info(f"Closed window: {win.title}")
            return
    log.warning(f"No window to close matching '{title_fragment}'")


# ─────────────────────────────────────────────────────────────
# ▸ APPLICATION LAUNCHER
# ─────────────────────────────────────────────────────────────

# Friendly name → executable / command mapping
APP_MAP: dict[str, str] = {
    "chrome":        "chrome.exe",
    "firefox":       "firefox.exe",
    "notepad":       "notepad.exe",
    "explorer":      "explorer.exe",
    "photoshop":     r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
    "vscode":        "code",
    "cmd":           "cmd.exe",
    "powershell":    "powershell.exe",
    "calculator":    "calc.exe",
    "paint":         "mspaint.exe",
    "wordpad":       "wordpad.exe",
}


def open_app(name: str, wait: float = 1.5):
    """
    Launch an application by friendly name or raw executable path.

    Args:
        name : A key from APP_MAP or a direct path / command.
        wait : Seconds to wait for the app to initialise.
    """
    cmd = APP_MAP.get(name.lower(), name)
    log.info(f"Launching app: '{name}'  →  {cmd}")
    try:
        subprocess.Popen(cmd, shell=True)
        time.sleep(wait)
    except Exception as exc:
        log.error(f"Failed to launch '{name}': {exc}")


def open_url_in_browser(url: str, browser: str = "chrome"):
    """Open a URL in the specified browser."""
    log.info(f"Opening URL in {browser}: {url}")
    open_app(browser)
    time.sleep(1.5)
    # Find the address bar and type the URL
    press_key("ctrl", "l")
    time.sleep(0.3)
    type_text(url)
    press_key("enter")


def run_shell_command(command: str, capture_output: bool = True) -> str:
    """
    Execute a shell command and return its stdout.

    Args:
        command        : The shell command string.
        capture_output : If True, return stdout; else stream to console.

    Returns:
        stdout as a string (or empty string on error).
    """
    log.info(f"Shell: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log.warning(f"Command exited with code {result.returncode}: {result.stderr.strip()}")
        return result.stdout.strip() if capture_output else ""
    except subprocess.TimeoutExpired:
        log.error(f"Command timed out: {command}")
        return ""
    except Exception as exc:
        log.error(f"Shell error: {exc}")
        return ""
