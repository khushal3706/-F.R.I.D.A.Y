"""
FRIDAY -- Setup & Dependency Checker (setup.py)
Run this ONCE before starting the agent.
Installs packages, verifies dependencies, creates dirs.

Usage:
    python setup.py
"""

import sys
import subprocess
import importlib
from pathlib import Path

# ── Force UTF-8 output on Windows terminals ───────────────────
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Terminal colours (no external deps) ──────────────────────
def _c(msg, code): return f"\033[{code}m{msg}\033[0m"
ok   = lambda m: print(_c(f"  [OK]  {m}", "32"))
warn = lambda m: print(_c(f"  [!!]  {m}", "33"))
err  = lambda m: print(_c(f"  [ERR] {m}", "31"))
info = lambda m: print(_c(f"  [i]   {m}", "36"))

BANNER = """
  ==========================================
    FRIDAY - Windows AI Agent Setup Wizard
  ==========================================
"""

# ─────────────────────────────────────────────────────────────
# ▸ STEP 1: Python version check
# ─────────────────────────────────────────────────────────────
def check_python():
    print("\n[1/5] Checking Python version …")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        err(f"Python 3.10+ required — you have {major}.{minor}")
        sys.exit(1)
    ok(f"Python {major}.{minor} ✓")


# ─────────────────────────────────────────────────────────────
# ▸ STEP 2: Install core requirements
# ─────────────────────────────────────────────────────────────
def install_requirements():
    print("\n[2/5] Installing pip packages from requirements.txt …")
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        err("requirements.txt not found!")
        return

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
        capture_output=False,
    )
    if result.returncode == 0:
        ok("All packages installed successfully.")
    else:
        err("Some packages failed to install — check output above.")


# ─────────────────────────────────────────────────────────────
# ▸ STEP 3: Verify critical imports
# ─────────────────────────────────────────────────────────────
REQUIRED_PACKAGES = [
    ("pyautogui",           "Mouse & keyboard control"),
    ("pygetwindow",         "Window management"),
    ("PIL",                 "Image I/O (Pillow)"),
    ("google.genai",        "Gemini 1.5 Flash — new SDK"),
    ("mss",                 "Fast screen capture (MSS)"),
    ("cv2",                 "Computer vision (OpenCV)"),
    ("httpx",               "HTTP client (Pollinations + Ollama)"),
    ("duckduckgo_search",   "Free web search"),
    ("rich",                "Terminal UI"),
    ("pyperclip",           "Clipboard access"),
]

OPTIONAL_PACKAGES = [
    ("pytesseract",  "OCR — extract text from screenshots"),
    ("diffusers",    "Stable Diffusion local image gen"),
    ("torch",        "PyTorch (for Stable Diffusion)"),
    ("win10toast",   "Windows toast notifications"),
]


def verify_imports():
    print("\n[3/5] Verifying imports …")
    all_ok = True
    for pkg, label in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            ok(f"{label}  [{pkg}]")
        except ImportError:
            err(f"MISSING: {label}  [{pkg}]")
            all_ok = False

    print("\n  Optional packages:")
    for pkg, label in OPTIONAL_PACKAGES:
        try:
            importlib.import_module(pkg)
            ok(f"{label}  [{pkg}]")
        except ImportError:
            warn(f"Not installed (optional): {label}  [{pkg}]")

    if not all_ok:
        err("\nSome required packages are missing. Re-run setup or install manually.")
    else:
        ok("\nAll required imports verified.")


# ─────────────────────────────────────────────────────────────
# ▸ STEP 4: Create project directories
# ─────────────────────────────────────────────────────────────
DIRS = [
    "screenshots",
    "generated_images",
    "logs",
]


def create_dirs():
    print("\n[4/5] Creating project directories …")
    base = Path(__file__).parent
    for d in DIRS:
        p = base / d
        p.mkdir(exist_ok=True)
        ok(f"Directory ready: {p}")


# ─────────────────────────────────────────────────────────────
# ▸ STEP 5: .env setup
# ─────────────────────────────────────────────────────────────
def setup_env():
    print("\n[5/5] Checking environment configuration …")
    base    = Path(__file__).parent
    env     = base / ".env"
    example = base / ".env.example"

    if env.exists():
        ok(".env already exists.")
    elif example.exists():
        import shutil
        shutil.copy(str(example), str(env))
        warn(".env created from .env.example — please add your API keys to .env before running friday.py!")
    else:
        warn(".env.example not found — create a .env file manually with your API keys.")

    # Check if Gemini key is still placeholder
    if env.exists():
        content = env.read_text()
        if "your-gemini-key-here" in content:
            warn("GEMINI_API_KEY is still the placeholder — update .env with your free key!")
            warn("  Get a free key at: https://aistudio.google.com/apikey")
        else:
            ok("GEMINI_API_KEY appears to be configured.")


# ─────────────────────────────────────────────────────────────
# ▸ MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(BANNER)
    check_python()
    install_requirements()
    verify_imports()
    create_dirs()
    setup_env()

    print("\n" + "─" * 60)
    print("  🚀  FRIDAY is ready!  Run with:")
    print()
    print("       python friday.py                  # Standard mode")
    print("       python friday.py --confirm        # Confirm before each action")
    print("       python friday.py --provider ollama  # Use local Llama model")
    print("─" * 60 + "\n")
