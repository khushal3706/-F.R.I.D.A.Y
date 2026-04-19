"""
╔══════════════════════════════════════════════════════════════╗
║      FRIDAY — Code Executor (core/executor.py)              ║
║  Safely executes LLM-generated Python in a sandboxed        ║
║  namespace with access to all FRIDAY tools                  ║
║  FREE STACK: no OpenAI references                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import traceback
import io
import sys
from core.logger import get_logger
from core.safety import is_killed

log = get_logger("Executor")


# ─────────────────────────────────────────────────────────────
# ▸ PRE-BUILT EXECUTION NAMESPACE
#   All FRIDAY tools available to LLM-generated code
# ─────────────────────────────────────────────────────────────
def _build_namespace() -> dict:
    """
    Build the global namespace injected into every code execution.
    Every tool here is callable directly by name in generated code.
    All imports are free / local — no paid API dependencies.
    """
    # ── System control ─────────────────────────────────────────
    from modules.system_control import (
        click, move_to, drag, scroll,
        type_text, press_key, hold_key,
        list_windows, focus_window, minimize_window, close_window,
        open_app, open_url_in_browser, run_shell_command,
    )
    # ── Screen context (MSS + OpenCV + Gemini Vision) ──────────
    from modules.screen_context import (
        take_screenshot, take_region_screenshot,
        extract_text, describe_screen,
        get_pixel_color, find_image_on_screen,
        screenshot_and_extract_text,
        pil_to_cv2, cv2_to_pil, preprocess_for_ocr,
    )
    # ── Web search (DuckDuckGo — free, no key) ─────────────────
    from modules.web_search import search, search_and_summarise

    # ── Image generation (Pollinations.ai — free, no key) ──────
    from modules.image_gen import generate_image, open_generated_image

    # ── Utilities ──────────────────────────────────────────────
    from modules.utils import (
        get_clipboard, set_clipboard,
        read_file, write_file, read_json, write_json,
        list_files, safe_copy, notify, timestamp,
    )

    # ── Standard library ───────────────────────────────────────
    import time, os, pathlib, subprocess, re, json, math

    return {
        # System control
        "click":               click,
        "move_to":             move_to,
        "drag":                drag,
        "scroll":              scroll,
        "type_text":           type_text,
        "press_key":           press_key,
        "hold_key":            hold_key,
        "list_windows":        list_windows,
        "focus_window":        focus_window,
        "minimize_window":     minimize_window,
        "close_window":        close_window,
        "open_app":            open_app,
        "open_url_in_browser": open_url_in_browser,
        "run_shell_command":   run_shell_command,
        # Screen context
        "take_screenshot":             take_screenshot,
        "take_region_screenshot":      take_region_screenshot,
        "extract_text":                extract_text,
        "describe_screen":             describe_screen,
        "screenshot_and_extract_text": screenshot_and_extract_text,
        "get_pixel_color":             get_pixel_color,
        "find_image_on_screen":        find_image_on_screen,
        "pil_to_cv2":                  pil_to_cv2,
        "cv2_to_pil":                  cv2_to_pil,
        "preprocess_for_ocr":          preprocess_for_ocr,
        # Web search
        "search":               search,
        "search_and_summarise": search_and_summarise,
        # Image generation
        "generate_image":       generate_image,
        "open_generated_image": open_generated_image,
        # Utilities
        "get_clipboard":        get_clipboard,
        "set_clipboard":        set_clipboard,
        "read_file":            read_file,
        "write_file":           write_file,
        "read_json":            read_json,
        "write_json":           write_json,
        "list_files":           list_files,
        "safe_copy":            safe_copy,
        "notify":               notify,
        "timestamp":            timestamp,
        # Standard library shortcuts
        "time":       time,
        "os":         os,
        "pathlib":    pathlib,
        "subprocess": subprocess,
        "re":         re,
        "json":       json,
        "math":       math,
        "print":      print,
    }


# ─────────────────────────────────────────────────────────────
# ▸ EXECUTION RESULT
# ─────────────────────────────────────────────────────────────
class ExecutionResult:
    """Outcome of a single code execution attempt."""

    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output  = output
        self.error   = error

    def __repr__(self):
        status = "OK" if self.success else "ERR"
        return f"ExecutionResult({status}  output={self.output[:60]!r})"


# ─────────────────────────────────────────────────────────────
# ▸ PYTHON CODE EXECUTOR
# ─────────────────────────────────────────────────────────────
def execute_code(code: str, confirm: bool = False) -> ExecutionResult:
    """
    Execute a Python code snippet inside FRIDAY's sandboxed namespace.

    Args:
        code    : Valid Python source code string (from LLM output).
        confirm : If True, show the code and ask [y/N] before running.

    Returns:
        ExecutionResult with success flag, stdout capture, and error trace.
    """
    if is_killed():
        log.warning("Kill-switch active — execution blocked.")
        return ExecutionResult(False, "", "Kill-switch is active.")

    # ── Optional human confirmation ───────────────────────────
    if confirm:
        print("\n" + "─" * 60)
        print("FRIDAY wants to execute the following code:")
        print("─" * 60)
        print(code)
        print("─" * 60)
        answer = input("Allow execution? [y/N]: ").strip().lower()
        if answer != "y":
            log.info("User declined execution.")
            return ExecutionResult(False, "", "User declined execution.")

    # ── Capture stdout ────────────────────────────────────────
    captured  = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    namespace = _build_namespace()
    success   = False
    error_msg = ""

    try:
        log.info(f"Executing code ({len(code)} chars) …")
        exec(compile(code, "<friday_generated>", "exec"), namespace)  # noqa: S102
        success = True
        log.info("Execution successful.")
    except Exception:
        error_msg = traceback.format_exc()
        log.error(f"Execution error:\n{error_msg}")
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    return ExecutionResult(success, output, error_msg)


# ─────────────────────────────────────────────────────────────
# ▸ SHELL COMMAND EXECUTOR
# ─────────────────────────────────────────────────────────────
def execute_shell(command: str) -> ExecutionResult:
    """
    Run a raw PowerShell/CMD command and return its output.

    Args:
        command : Shell command string.

    Returns:
        ExecutionResult with stdout as output.
    """
    if is_killed():
        return ExecutionResult(False, "", "Kill-switch is active.")

    from modules.system_control import run_shell_command
    output  = run_shell_command(command)
    success = output is not None
    return ExecutionResult(success, output or "")
