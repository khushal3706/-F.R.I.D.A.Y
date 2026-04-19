"""
╔══════════════════════════════════════════════════════════════╗
║              FRIDAY AI Agent — Configuration                 ║
║         All API keys, paths, and constants go here          ║
║         100% FREE STACK — No paid APIs required             ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# ▸ PATHS
# ─────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
GENERATED_DIR   = BASE_DIR / "generated_images"
LOGS_DIR        = BASE_DIR / "logs"

for _dir in [SCREENSHOTS_DIR, GENERATED_DIR, LOGS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# ▸ API KEYS
#   Gemini AI Studio is FREE:  https://aistudio.google.com/apikey
#   DuckDuckGo search = NO key needed
#   Pollinations.ai   = NO key needed
# ─────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# ▸ LLM SETTINGS  (Gemini Flash — free tier)
# ─────────────────────────────────────────────────────────────
LLM_PROVIDER    = "gemini"            # "gemini" | "ollama"
GEMINI_MODEL    = "gemini-flash-latest" # Free tier on AI Studio
OLLAMA_MODEL    = "llama3"            # Local model name (Ollama)
OLLAMA_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT = """
You are FRIDAY, an advanced AI agent running on Windows.
You can control the computer, browse the web, generate images, and execute code.
When a user asks you to perform a task, respond ONLY with valid Python code
wrapped in a ```python ... ``` block if execution is needed.
For conversational answers, respond naturally without a code block.
Always confirm destructive actions before executing.
""".strip()

# ─────────────────────────────────────────────────────────────
# ▸ IMAGE GENERATION  (Pollinations.ai — completely free, no key)
# ─────────────────────────────────────────────────────────────
IMAGE_PROVIDER       = "pollinations"      # "pollinations" | "stable_diffusion"
POLLINATIONS_MODEL   = "flux"              # flux | turbo | dreamshaper
POLLINATIONS_WIDTH   = 1024
POLLINATIONS_HEIGHT  = 1024

# Stable Diffusion (local via diffusers — optional)
SD_MODEL_ID = "runwayml/stable-diffusion-v1-5"

# ─────────────────────────────────────────────────────────────
# ▸ SCREEN CAPTURE  (MSS — faster than PIL ImageGrab)
# ─────────────────────────────────────────────────────────────
SCREEN_CAPTURE_BACKEND = "mss"   # "mss" | "pillow"

# ─────────────────────────────────────────────────────────────
# ▸ WEB SEARCH  (DuckDuckGo — no API key required)
# ─────────────────────────────────────────────────────────────
SEARCH_PROVIDER    = "duckduckgo"
SEARCH_MAX_RESULTS = 5

# ─────────────────────────────────────────────────────────────
# ▸ SAFETY SETTINGS
# ─────────────────────────────────────────────────────────────
KILL_SWITCH_CORNER_RADIUS  = 50
KILL_SWITCH_ACTIVE_CORNER  = "top_left"
PYAUTOGUI_FAILSAFE         = True
PYAUTOGUI_PAUSE            = 0.3

# ─────────────────────────────────────────────────────────────
# ▸ LOGGING
# ─────────────────────────────────────────────────────────────
LOG_LEVEL    = "INFO"
LOG_TO_FILE  = True
LOG_FILENAME = LOGS_DIR / "friday.log"

# ─────────────────────────────────────────────────────────────
# ▸ AGENT LOOP
# ─────────────────────────────────────────────────────────────
AGENT_HISTORY_LIMIT = 20
SCREENSHOT_ON_ERROR = True
