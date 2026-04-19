"""
╔══════════════════════════════════════════════════════════════╗
║     FRIDAY — Example Usage Scripts (examples/demo.py)       ║
║  Standalone demos — no full REPL needed                     ║
║  FREE STACK: Gemini | DuckDuckGo | Pollinations | MSS+CV2   ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python examples/demo.py <demo_name>

Available demos:
    screenshot    Capture screen + Gemini Vision description
    search        DuckDuckGo web search (no key needed)
    image         Generate image via Pollinations.ai (no key needed)
    type          Open Notepad and type a message
    windows       List all open windows
    vision        Screenshot + OpenCV preprocessing + describe
    plan          Multi-step goal planner (needs Gemini key)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env before any module imports
from pathlib import Path as _P
_env = _P(__file__).parent.parent / ".env"
if _env.exists():
    for _ln in _env.read_text(encoding="utf-8").splitlines():
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _, _v = _ln.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from core.safety import start_kill_switch_watcher


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: SCREENSHOT + GEMINI VISION
# ─────────────────────────────────────────────────────────────
def demo_screenshot():
    """Capture full screen with MSS and describe it via Gemini Vision."""
    from modules.screen_context import take_screenshot, describe_screen
    print("Capturing screen with MSS ...")
    img  = take_screenshot(prefix="demo")
    print("   Saved to screenshots/\n")

    print("Asking Gemini Vision to describe the screen ...")
    desc = describe_screen(img, question="Describe what is visible on the screen in detail.")
    print(f"\n[Gemini Vision]\n{desc}\n")


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: OPENCV VISION PIPELINE
# ─────────────────────────────────────────────────────────────
def demo_vision():
    """MSS capture → OpenCV preprocessing → OCR → Gemini description."""
    from modules.screen_context import (
        take_screenshot, preprocess_for_ocr,
        extract_text, describe_screen, pil_to_cv2,
    )
    import cv2

    print("Step 1: Capture screen with MSS ...")
    img = take_screenshot(save=True, prefix="vision_demo")

    print("Step 2: OpenCV preprocessing for OCR ...")
    img_cv = pil_to_cv2(img)
    # Show image dimensions + channel info
    h, w, c = img_cv.shape
    print(f"   Screen size: {w}x{h}  channels: {c}")

    print("Step 3: Extract text (OCR) ...")
    text = extract_text(img, preprocess=True)
    if text:
        print(f"   OCR text ({len(text)} chars):\n   {text[:300]}\n")
    else:
        print("   (No text found — install Tesseract for OCR support)\n")

    print("Step 4: Gemini Vision description ...")
    desc = describe_screen(img)
    print(f"\n[Gemini]\n{desc}\n")


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: DUCKDUCKGO SEARCH
# ─────────────────────────────────────────────────────────────
def demo_search():
    """Free DuckDuckGo web search — no API key required."""
    from modules.web_search import search_and_summarise
    query = "Python AI agent open source 2025"
    print(f"Searching DuckDuckGo: {query!r}\n")
    print(search_and_summarise(query, max_results=3))


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: POLLINATIONS.AI IMAGE GENERATION
# ─────────────────────────────────────────────────────────────
def demo_image():
    """Generate an image via Pollinations.ai — completely free, no key needed."""
    from modules.image_gen import generate_image, open_generated_image
    prompt = "A futuristic AI assistant hologram floating above a sleek desk, cyberpunk style, neon blue glow"
    print(f"Generating image via Pollinations.ai (free):\n  {prompt}\n")
    path = generate_image(prompt, provider="pollinations", model="flux")
    print(f"[OK] Saved: {path}")
    open_generated_image(path)


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: TYPE TEXT
# ─────────────────────────────────────────────────────────────
def demo_type():
    """Open Notepad and type a message automatically."""
    import time
    from modules.system_control import open_app, type_text, press_key
    print("Opening Notepad ...")
    open_app("notepad")
    time.sleep(1.5)
    type_text("Hello! I am FRIDAY, your free AI assistant.", interval=0.05)
    press_key("enter")
    type_text("Running on: Gemini Flash | DuckDuckGo | Pollinations.ai | MSS+OpenCV", interval=0.04)
    press_key("enter")
    type_text("Total API cost: $0.00", interval=0.05)
    print("[OK] Done typing.")


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: LIST WINDOWS
# ─────────────────────────────────────────────────────────────
def demo_windows():
    """List all currently visible windows."""
    from modules.system_control import list_windows
    wins = list_windows()
    print(f"Open windows ({len(wins)}):")
    for i, w in enumerate(wins, 1):
        print(f"  [{i:>2}]  {w}")


# ─────────────────────────────────────────────────────────────
# ▸ DEMO: MULTI-STEP PLAN  (needs GEMINI_API_KEY in .env)
# ─────────────────────────────────────────────────────────────
def demo_plan():
    """Use Gemini to decompose a goal and execute it step-by-step."""
    from core.llm_brain import FridayBrain
    from core.planner   import Planner

    brain   = FridayBrain(provider="gemini")
    planner = Planner(brain)

    goal = "Open Chrome, go to wikipedia.org, and take a screenshot of the page"
    print(f"Goal: {goal}\n")

    plan = planner.make_plan(goal)
    print(plan.summary())
    print()

    confirm = input("Execute this plan? [y/N]: ").strip().lower()
    if confirm == "y":
        planner.execute_plan(plan, confirm=True)
    else:
        print("Execution cancelled.")


# ─────────────────────────────────────────────────────────────
# ▸ ENTRY POINT
# ─────────────────────────────────────────────────────────────
DEMOS = {
    "screenshot": demo_screenshot,
    "vision":     demo_vision,
    "search":     demo_search,
    "image":      demo_image,
    "type":       demo_type,
    "windows":    demo_windows,
    "plan":       demo_plan,
}

if __name__ == "__main__":
    start_kill_switch_watcher()

    if len(sys.argv) < 2 or sys.argv[1] not in DEMOS:
        print(__doc__)
        print("Available:", ", ".join(DEMOS.keys()))
        sys.exit(1)

    demo_name = sys.argv[1]
    print(f"\n{'='*60}")
    print(f"  FRIDAY Demo: {demo_name}")
    print(f"{'='*60}\n")

    try:
        DEMOS[demo_name]()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback; traceback.print_exc()
