"""
╔══════════════════════════════════════════════════════════════╗
║   FRIDAY — Image Generation (modules/image_gen.py)          ║
║  FREE STACK:                                                ║
║    Pollinations.ai — no key, no cost, runs online           ║
║    Stable Diffusion (diffusers) — local, no key             ║
╚══════════════════════════════════════════════════════════════╝
"""

import re
import urllib.parse
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
from config import (
    IMAGE_PROVIDER, GENERATED_DIR,
    POLLINATIONS_MODEL, POLLINATIONS_WIDTH, POLLINATIONS_HEIGHT,
    SD_MODEL_ID,
)

log = get_logger("ImageGen")


# ─────────────────────────────────────────────────────────────
# ▸ HELPERS
# ─────────────────────────────────────────────────────────────
def _safe_filename(prompt: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", prompt.lower())
    return "_".join(clean.split())[:40]


def _output_path(prompt: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{timestamp}_{_safe_filename(prompt)}.png"
    return Path(GENERATED_DIR) / name


# ─────────────────────────────────────────────────────────────
# ▸ POLLINATIONS.AI  (100% free, no API key needed)
# ─────────────────────────────────────────────────────────────
def _generate_pollinations(
    prompt: str,
    model: str | None = None,
    width: int | None = None,
    height: int | None = None,
    seed: int | None = None,
    enhance: bool = True,
    nologo: bool = True,
) -> Path:
    """
    Generate an image via Pollinations.ai — free, no account needed.

    API docs: https://pollinations.ai/

    Supported models:
        flux          — Flux (default, high quality)
        turbo         — Faster, slightly lower quality
        dreamshaper   — Artistic style
        flux-realism  — Photo-realistic

    Args:
        prompt  : Text description of the image.
        model   : Model override (defaults to config POLLINATIONS_MODEL).
        width   : Output width in pixels (default 1024).
        height  : Output height in pixels (default 1024).
        seed    : Random seed for reproducibility (-1 = random).
        enhance : Let Pollinations auto-enhance the prompt.
        nologo  : Remove Pollinations watermark.

    Returns:
        Path to the saved PNG.
    """
    try:
        import httpx
    except ImportError:
        raise ImportError("Run: pip install httpx")

    _model  = model  or POLLINATIONS_MODEL
    _width  = width  or POLLINATIONS_WIDTH
    _height = height or POLLINATIONS_HEIGHT

    # URL-encode the prompt
    encoded_prompt = urllib.parse.quote(prompt)

    # Build request URL
    params = {
        "width":   _width,
        "height":  _height,
        "model":   _model,
        "enhance": str(enhance).lower(),
        "nologo":  str(nologo).lower(),
    }
    if seed is not None and seed >= 0:
        params["seed"] = seed

    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{param_str}"

    log.info(f"Pollinations.ai generating ({_model}): {prompt[:80]}…")
    log.debug(f"URL: {url}")

    # Pollinations can take a few seconds to generate
    response = httpx.get(url, timeout=90, follow_redirects=True)
    response.raise_for_status()

    # Verify we got an image (not an error page)
    content_type = response.headers.get("content-type", "")
    if "image" not in content_type:
        raise ValueError(
            f"Pollinations returned non-image content ({content_type}).\n"
            f"Response: {response.text[:300]}"
        )

    out_path = _output_path(prompt)
    out_path.write_bytes(response.content)
    log.info(f"Image saved → {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────
# ▸ HUGGING FACE INFERENCE API  (free tier with HF token)
# ─────────────────────────────────────────────────────────────
def _generate_huggingface(prompt: str, model_id: str = "stabilityai/stable-diffusion-2-1") -> Path:
    """
    Generate via Hugging Face Inference API (free tier — rate limited).
    Get a free token: https://huggingface.co/settings/tokens

    Set in .env:   HF_API_TOKEN=hf_your_token_here
    """
    import os
    try:
        import httpx
    except ImportError:
        raise ImportError("Run: pip install httpx")

    hf_token = os.getenv("HF_API_TOKEN", "")
    if not hf_token:
        raise ValueError(
            "HF_API_TOKEN not set in .env.\n"
            "Get a free token at https://huggingface.co/settings/tokens"
        )

    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": prompt}

    log.info(f"HuggingFace generating ({model_id}): {prompt[:80]}…")
    response = httpx.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    out_path = _output_path(prompt)
    out_path.write_bytes(response.content)
    log.info(f"HF image saved → {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────
# ▸ STABLE DIFFUSION LOCAL  (diffusers — offline, needs GPU)
# ─────────────────────────────────────────────────────────────
_sd_pipeline = None


def _load_sd_pipeline():
    """Lazy-load SD pipeline (downloaded once from HuggingFace hub)."""
    global _sd_pipeline
    if _sd_pipeline is not None:
        return _sd_pipeline

    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError:
        raise ImportError("Run: pip install diffusers transformers torch accelerate")

    log.info(f"Loading SD pipeline: {SD_MODEL_ID} …")
    import torch as _torch
    device = "cuda" if _torch.cuda.is_available() else "cpu"
    dtype  = _torch.float16 if device == "cuda" else _torch.float32

    _sd_pipeline = StableDiffusionPipeline.from_pretrained(
        SD_MODEL_ID, torch_dtype=dtype
    ).to(device)
    log.info(f"SD pipeline loaded on {device.upper()}.")
    return _sd_pipeline


def _generate_stable_diffusion(
    prompt: str,
    negative_prompt: str = "blurry, ugly, deformed, watermark",
    steps: int = 25,
    guidance_scale: float = 7.5,
) -> Path:
    pipe   = _load_sd_pipeline()
    output = pipe(prompt=prompt, negative_prompt=negative_prompt,
                  num_inference_steps=steps, guidance_scale=guidance_scale)
    img = output.images[0]
    out_path = _output_path(prompt)
    img.save(out_path)
    log.info(f"SD image saved → {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────
# ▸ PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────
def generate_image(prompt: str, provider: str | None = None, **kwargs) -> Path:
    """
    Generate an image from a text prompt.

    Args:
        prompt   : Description of the image to create.
        provider : 'pollinations' (default, free) |
                   'huggingface' (free tier, needs HF token) |
                   'stable_diffusion' (local, needs GPU)
        **kwargs : Passed to the backend function.

    Returns:
        Path to the generated PNG file.
    """
    backend = (provider or IMAGE_PROVIDER).lower()

    if backend == "pollinations":
        return _generate_pollinations(prompt, **kwargs)
    elif backend in ("huggingface", "hf"):
        return _generate_huggingface(prompt, **kwargs)
    elif backend in ("stable_diffusion", "sd", "diffusers"):
        return _generate_stable_diffusion(prompt, **kwargs)
    else:
        raise ValueError(
            f"Unknown image provider: {backend!r}\n"
            "  Valid: 'pollinations' | 'huggingface' | 'stable_diffusion'"
        )


def open_generated_image(path: Path):
    """Open a generated image in the default Windows viewer."""
    import subprocess
    log.info(f"Opening image: {path}")
    subprocess.Popen(["start", str(path)], shell=True)
