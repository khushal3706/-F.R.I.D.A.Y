"""
╔══════════════════════════════════════════════════════════════╗
║      FRIDAY — Terminal Interface (friday.py)                ║
║  The main entry point: REPL loop with rich CLI output       ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python friday.py [--confirm] [--provider openai|ollama] [--no-safety]

Flags:
    --confirm     Require y/N confirmation before executing any code
    --provider    Override the default LLM provider from config.py
    --no-safety   Disable the kill-switch watcher (not recommended)
"""

# ── Load .env FIRST so os.getenv() in config.py sees the keys ────
import os
from pathlib import Path
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import sys
import argparse
import time

# ── Pretty terminal output ────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel   import Panel
    from rich.syntax  import Syntax
    from rich.table   import Table
    from rich.text    import Text
    _RICH = True
except ImportError:
    _RICH = False


def _print(msg: str, style: str = ""):
    if _RICH and "console" in globals():
        console.print(msg, style=style)
    else:
        print(msg)


# ─────────────────────────────────────────────────────────────
# ▸ COMMAND ROUTER
#   Built-in slash commands processed BEFORE sending to LLM
# ─────────────────────────────────────────────────────────────
BUILT_IN_COMMANDS = {
    "/help":      "Show this help message",
    "/reset":     "Clear conversation memory",
    "/screen":    "Take a screenshot and describe the screen",
    "/search":    "Search the web  —  usage: /search <query>",
    "/image":     "Generate an image  —  usage: /image <prompt>",
    "/windows":   "List all open windows",
    "/open":      "Open an app  —  usage: /open <app name>",
    "/shell":     "Run a shell command  —  usage: /shell <command>",
    "/status":    "Show agent status",
    "/kill":      "Manually trigger the kill-switch",
    "/quit":      "Exit FRIDAY",
}


def show_help(console_obj=None):
    if _RICH and console_obj:
        table = Table(title="FRIDAY Built-in Commands", style="cyan", border_style="bright_blue")
        table.add_column("Command", style="bold yellow", no_wrap=True)
        table.add_column("Description", style="white")
        for cmd, desc in BUILT_IN_COMMANDS.items():
            table.add_row(cmd, desc)
        console_obj.print(table)
    else:
        print("\nFRIDAY Built-in Commands:")
        for cmd, desc in BUILT_IN_COMMANDS.items():
            print(f"  {cmd:<12} {desc}")


def handle_builtin(cmd_line: str, brain, args) -> bool:
    """
    Handle a built-in slash command.
    Returns True if the line was a built-in command, False otherwise.
    """
    parts = cmd_line.strip().split(None, 1)
    cmd   = parts[0].lower()
    rest  = parts[1] if len(parts) > 1 else ""

    if cmd == "/help":
        show_help(console if _RICH else None)

    elif cmd == "/reset":
        brain.reset()
        _print("✅  Memory cleared.", "green")

    elif cmd == "/screen":
        from modules.screen_context import take_screenshot, describe_screen
        _print("📸  Capturing screen …", "yellow")
        img  = take_screenshot()
        desc = describe_screen(img)
        _print(f"\n🖥️  Screen description:\n{desc}\n", "cyan")

    elif cmd == "/search":
        if not rest:
            _print("Usage: /search <query>", "red")
            return True
        from modules.web_search import search_and_summarise
        _print(f"🔍  Searching: {rest}", "yellow")
        summary = search_and_summarise(rest)
        _print(summary, "white")

    elif cmd == "/image":
        if not rest:
            _print("Usage: /image <prompt>", "red")
            return True
        from modules.image_gen import generate_image, open_generated_image
        _print(f"🎨  Generating image: {rest}", "yellow")
        path = generate_image(rest)
        _print(f"✅  Saved: {path}", "green")
        open_generated_image(path)

    elif cmd == "/windows":
        from modules.system_control import list_windows
        wins = list_windows()
        _print(f"\n🪟  Open windows ({len(wins)}):", "cyan")
        for w in wins:
            _print(f"   • {w}", "white")
        print()

    elif cmd == "/open":
        if not rest:
            _print("Usage: /open <app name>", "red")
            return True
        from modules.system_control import open_app
        open_app(rest)
        _print(f"✅  Launched: {rest}", "green")

    elif cmd == "/shell":
        if not rest:
            _print("Usage: /shell <command>", "red")
            return True
        from core.executor import execute_shell
        result = execute_shell(rest)
        status = "green" if result.success else "red"
        _print(result.output or "(no output)", status)

    elif cmd == "/status":
        from core.safety import is_killed
        from config import GEMINI_MODEL, OLLAMA_MODEL
        model_name = GEMINI_MODEL if brain.provider == "gemini" else OLLAMA_MODEL
        _print(f"\n📊  FRIDAY Status", "bold cyan")
        _print(f"   Provider    : {brain.provider.upper()}", "white")
        _print(f"   Model       : {model_name}", "white")
        _print(f"   Memory      : {len(brain.memory)} messages", "white")
        _print(f"   Search      : DuckDuckGo (free)", "white")
        _print(f"   Images      : Pollinations.ai (free)", "white")
        _print(f"   Vision      : MSS + OpenCV + Gemini (free)", "white")
        _print(f"   Kill-switch : {'ACTIVE' if is_killed() else 'Armed — move mouse to top-left'}", "red" if is_killed() else "green")
        print()

    elif cmd == "/kill":
        from core.safety import trigger_kill
        trigger_kill("Manual /kill command")
        _print("🛑  Kill-switch triggered. Exiting …", "bold red")
        sys.exit(0)

    elif cmd in ("/quit", "/exit", "/q"):
        _print("👋  Goodbye!", "bold cyan")
        sys.exit(0)

    else:
        return False   # Not a built-in command

    return True


# ─────────────────────────────────────────────────────────────
# ▸ MAIN AGENT LOOP
# ─────────────────────────────────────────────────────────────
def run_agent(args: argparse.Namespace):
    from core.llm_brain import FridayBrain
    from core.executor  import execute_code
    from core.safety    import start_kill_switch_watcher, is_killed

    if _RICH:
        console.print(
            Panel.fit(
                "[bold cyan]F R I D A Y[/bold cyan]  [white]AI Agent — Windows Edition[/white]\n"
                "[dim]Type a command, a question, or use /help for built-ins.[/dim]\n"
                "[dim yellow]Kill-switch: move mouse to TOP-LEFT corner[/dim yellow]",
                border_style="bright_blue",
            )
        )
    else:
        print("=" * 60)
        print("  FRIDAY AI Agent — Windows Edition")
        print("  /help for commands  |  Top-left corner = kill switch")
        print("=" * 60)

    # ── Safety watcher ─────────────────────────────────────────
    if not args.no_safety:   # argparse converts --no-safety → no_safety
        start_kill_switch_watcher()

    # ── Brain ──────────────────────────────────────────────────
    brain = FridayBrain(provider=args.provider)

    # ── REPL ───────────────────────────────────────────────────
    while not is_killed():
        try:
            if _RICH:
                user_input = console.input("[bold green]You ❯[/bold green] ").strip()
            else:
                user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            _print("\n👋  Interrupted. Goodbye!", "bold cyan")
            break

        if not user_input:
            continue

        # ── Built-in slash commands ────────────────────────────
        if user_input.startswith("/"):
            handle_builtin(user_input, brain, args)
            continue

        # ── LLM reasoning ─────────────────────────────────────
        _print("\n🤖  FRIDAY is thinking …", "dim yellow")
        try:
            reply, code = brain.think(user_input)
        except Exception as exc:
            _print(f"❌  Brain error: {exc}", "bold red")
            continue

        # ── Print reply ────────────────────────────────────────
        print()
        if _RICH:
            console.print(Panel(reply, title="[bold cyan]FRIDAY[/bold cyan]", border_style="cyan"))
        else:
            print(f"FRIDAY: {reply}")

        # ── Execute code if present ────────────────────────────
        if code:
            if _RICH:
                console.print(
                    Panel(
                        Syntax(code, "python", theme="monokai", line_numbers=True),
                        title="[yellow]Generated Code[/yellow]",
                        border_style="yellow",
                    )
                )
            else:
                print(f"\n--- Code ---\n{code}\n------------")

            result = execute_code(code, confirm=args.confirm)

            if result.output:
                _print(f"\n📤  Output:\n{result.output}", "white")
            if result.error:
                _print(f"\n❌  Error:\n{result.error}", "red")
                if result.error:
                    # Feed error back to brain for self-correction
                    brain.inject_context(f"The code raised an error:\n{result.error}\nPlease correct it.")

        print()   # spacing


# ─────────────────────────────────────────────────────────────
# ▸ ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FRIDAY — Windows AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Require confirmation before executing LLM-generated code",
    )
    parser.add_argument(
        "--provider", default=None,
        choices=["openai", "ollama"],
        help="LLM provider override (default: from config.py)",
    )
    parser.add_argument(
        "--no-safety", action="store_true",
        help="Disable the kill-switch watcher (not recommended)",
    )
    args = parser.parse_args()

    # Initialise Rich console at module level if available
    if _RICH:
        console = Console()

    run_agent(args)
