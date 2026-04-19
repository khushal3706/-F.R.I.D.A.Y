"""
╔══════════════════════════════════════════════════════════════╗
║        FRIDAY — Safety Kill-Switch (core/safety.py)         ║
║  Monitors mouse position; terminates all automation         ║
║  immediately when mouse enters a designated corner.         ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import math
import threading
import pyautogui
from core.logger import get_logger
from config import KILL_SWITCH_CORNER_RADIUS, KILL_SWITCH_ACTIVE_CORNER, PYAUTOGUI_FAILSAFE

log = get_logger("Safety")

# ── Global kill flag ──────────────────────────────────────────────────────────
_killed = threading.Event()


def is_killed() -> bool:
    """Returns True if the kill-switch has been triggered."""
    return _killed.is_set()


def trigger_kill(reason: str = "Manual kill-switch activated"):
    """
    Immediately set the kill flag. 
    Any running action loop should check is_killed() regularly.
    """
    _killed.set()
    log.critical(f"🛑  KILL SWITCH TRIGGERED — {reason}")


def reset_kill():
    """Re-arm the kill-switch after a safe stop."""
    _killed.clear()
    log.info("Kill-switch reset — agent is safe to restart.")


# ── Corner detection ──────────────────────────────────────────────────────────
def _get_corner_coords() -> tuple[int, int]:
    """Return pixel coordinates of the active kill-switch corner."""
    sw, sh = pyautogui.size()
    corners = {
        "top_left":     (0,  0),
        "top_right":    (sw, 0),
        "bottom_left":  (0,  sh),
        "bottom_right": (sw, sh),
    }
    return corners.get(KILL_SWITCH_ACTIVE_CORNER, (0, 0))


def _is_in_corner(x: int, y: int, cx: int, cy: int, radius: int) -> bool:
    """Check if (x, y) is within `radius` pixels of corner (cx, cy)."""
    return math.hypot(x - cx, y - cy) <= radius


# ── Background watcher thread ─────────────────────────────────────────────────
def _watcher_loop():
    """
    Polls the mouse position every 100 ms.
    Triggers the kill-switch if the cursor enters the designated corner.
    """
    cx, cy = _get_corner_coords()
    log.info(
        f"Kill-switch watching corner '{KILL_SWITCH_ACTIVE_CORNER}' "
        f"({cx}, {cy}) ± {KILL_SWITCH_CORNER_RADIUS}px"
    )

    while not _killed.is_set():
        try:
            x, y = pyautogui.position()
            if _is_in_corner(x, y, cx, cy, KILL_SWITCH_CORNER_RADIUS):
                trigger_kill("Mouse moved to kill-switch corner")
                sys.exit(0)   # Hard stop the process
        except Exception as exc:
            log.error(f"Kill-switch watcher error: {exc}")
        threading.Event().wait(0.1)   # 100 ms poll interval


def start_kill_switch_watcher():
    """
    Launch the kill-switch watcher in a daemon thread.
    Call this once at agent startup.
    """
    if PYAUTOGUI_FAILSAFE:
        pyautogui.FAILSAFE = True     # Built-in PyAutoGUI top-left failsafe
        log.info("PyAutoGUI built-in failsafe ENABLED (top-left corner).")

    watcher = threading.Thread(target=_watcher_loop, daemon=True, name="KillSwitchWatcher")
    watcher.start()
    log.info("Kill-switch watcher thread started.")
    return watcher
