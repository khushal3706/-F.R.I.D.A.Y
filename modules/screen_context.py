"""
╔══════════════════════════════════════════════════════════════╗
║   FRIDAY — Screen Context (modules/screen_context.py)       ║
║  FREE STACK: MSS (fast capture) + OpenCV + Gemini Vision    ║
╚══════════════════════════════════════════════════════════════╝
"""

import time
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
from config import SCREENSHOTS_DIR, SCREEN_CAPTURE_BACKEND, GEMINI_API_KEY, GEMINI_MODEL

log = get_logger("ScreenContext")


# ─────────────────────────────────────────────────────────────
# ▸ SCREENSHOT CAPTURE  (MSS — faster than PIL ImageGrab)
# ─────────────────────────────────────────────────────────────
def take_screenshot(
    region: dict | None = None,
    save: bool = True,
    prefix: str = "screen",
):
    """
    Capture the current screen using MSS (primary) or Pillow (fallback).

    Args:
        region : MSS monitor dict e.g. {"top":0,"left":0,"width":1920,"height":1080}
                 or None for the full primary monitor.
        save   : Save as PNG to the screenshots directory.
        prefix : Filename prefix.

    Returns:
        PIL Image object (converted from MSS output).
    """
    from PIL import Image

    if SCREEN_CAPTURE_BACKEND == "mss":
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                monitor = region if region else sct.monitors[1]  # monitor[1] = primary
                sct_img = sct.grab(monitor)
                # MSS returns BGRA — convert to PIL RGB
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except ImportError:
            log.warning("mss not installed — falling back to Pillow ImageGrab.")
            img = _pillow_grab(region)
    else:
        img = _pillow_grab(region)

    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = Path(SCREENSHOTS_DIR) / f"{prefix}_{timestamp}.png"
        img.save(path)
        log.info(f"Screenshot saved → {path}")

    return img


def _pillow_grab(region=None):
    """Fallback: capture using Pillow ImageGrab."""
    from PIL import ImageGrab, Image
    if isinstance(region, dict):
        bbox = (region["left"], region["top"],
                region["left"] + region["width"],
                region["top"]  + region["height"])
    else:
        bbox = None
    return ImageGrab.grab(bbox=bbox)


def take_region_screenshot(left: int, top: int, width: int, height: int, **kwargs):
    """Capture a screen region by (left, top, width, height)."""
    region = {"top": top, "left": left, "width": width, "height": height}
    return take_screenshot(region=region, **kwargs)


# ─────────────────────────────────────────────────────────────
# ▸ OPENCV UTILITIES
# ─────────────────────────────────────────────────────────────
def pil_to_cv2(img):
    """Convert a PIL Image to an OpenCV numpy array (BGR)."""
    import numpy as np
    import cv2
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def cv2_to_pil(img_cv2):
    """Convert an OpenCV BGR array to a PIL Image."""
    import cv2
    from PIL import Image
    import numpy as np
    rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def preprocess_for_ocr(img, scale: float = 2.0):
    """
    Upscale + threshold the image for better OCR accuracy.
    Uses OpenCV if available, otherwise falls back to Pillow.
    """
    try:
        import cv2
        import numpy as np
        img_cv = pil_to_cv2(img)
        # Greyscale + resize
        grey = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        h, w = grey.shape
        grey = cv2.resize(grey, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        # Adaptive threshold (better than simple contrast boost)
        grey = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)
        from PIL import Image
        return Image.fromarray(grey)
    except ImportError:
        # Pillow fallback
        from PIL import ImageEnhance
        grey = img.convert("L")
        grey = grey.resize((int(grey.width * scale), int(grey.height * scale)))
        return ImageEnhance.Contrast(grey).enhance(2.0)


# ─────────────────────────────────────────────────────────────
# ▸ OCR  (pytesseract — free, local)
# ─────────────────────────────────────────────────────────────
def extract_text(img, preprocess: bool = True) -> str:
    """
    Run OCR on a PIL image and return detected text.
    Requires: Tesseract installed on PATH + pip install pytesseract
    Download: https://github.com/UB-Mannheim/tesseract/wiki
    """
    try:
        import pytesseract
    except ImportError:
        log.warning("pytesseract not installed — OCR disabled. Run: pip install pytesseract")
        return ""

    if preprocess:
        img = preprocess_for_ocr(img)

    text = pytesseract.image_to_string(img)
    log.debug(f"OCR extracted {len(text)} characters.")
    return text.strip()


def screenshot_and_extract_text(region=None) -> tuple:
    """One-shot: capture screen + OCR text. Returns (PIL Image, str)."""
    img = take_screenshot(region=region)
    return img, extract_text(img)


# ─────────────────────────────────────────────────────────────
# ▸ SCREEN DESCRIPTION  (Gemini Vision — free)
# ─────────────────────────────────────────────────────────────
def describe_screen(img=None, question: str = "What is on the screen?") -> str:
    """
    Send the screenshot to Gemini Vision for a natural-language description.
    Falls back to OCR text if Gemini is unavailable.

    Args:
        img      : PIL Image (captures fresh screenshot if None).
        question : Question to ask about the screen.

    Returns:
        Gemini's description as a string.
    """
    if img is None:
        img = take_screenshot(save=False)

    try:
        from google import genai
    except ImportError:
        log.warning("google-genai not installed — falling back to OCR.")
        return extract_text(img) or "(Could not describe screen)"

    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set — falling back to OCR.")
        return extract_text(img) or "(No API key set)"

    client = genai.Client(api_key=GEMINI_API_KEY)

    log.info("Sending screenshot to Gemini Vision …")
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[question, img]
    )
    description = response.text.strip()
    log.info(f"Vision response: {description[:120]}…")
    return description


# ─────────────────────────────────────────────────────────────
# ▸ TEMPLATE MATCHING  (OpenCV — find image on screen)
# ─────────────────────────────────────────────────────────────
def find_image_on_screen(template_path: str, threshold: float = 0.8) -> tuple | None:
    """
    Locate a template image on the current screen using OpenCV template matching.
    Free alternative to PyAutoGUI's locateCenterOnScreen (no dependency on opencv-contrib).

    Args:
        template_path : Path to the template PNG file.
        threshold     : Match confidence (0–1). Higher = stricter.

    Returns:
        (x, y) centre coordinates if found, else None.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        log.error("opencv-python not installed. Run: pip install opencv-python")
        return None

    screen = take_screenshot(save=False)
    screen_cv = pil_to_cv2(screen)

    template = cv2.imread(template_path)
    if template is None:
        log.error(f"Template not found: {template_path}")
        return None

    result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        th, tw = template.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        log.info(f"Template found @ ({cx}, {cy})  confidence={max_val:.2f}")
        return cx, cy

    log.debug(f"Template not found (best match={max_val:.2f} < {threshold})")
    return None


# ─────────────────────────────────────────────────────────────
# ▸ PIXEL COLOR
# ─────────────────────────────────────────────────────────────
def get_pixel_color(x: int, y: int) -> tuple:
    """Return the (R, G, B) color of pixel at screen coordinates (x, y)."""
    region = {"top": y, "left": x, "width": 1, "height": 1}
    img = take_screenshot(region=region, save=False)
    color = img.getpixel((0, 0))
    log.debug(f"Pixel @ ({x},{y}) = {color}")
    return color[:3]
