
import os
import asyncio
import aiohttp
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

HF_API_URL = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models")
# Comma-separated list of models in priority order. You can override at runtime.
HF_IMAGE_MODELS = [
    m.strip() for m in os.getenv(
        "HF_IMAGE_MODELS",
        "stabilityai/sdxl-turbo,black-forest-labs/FLUX.1-schnell,stabilityai/stable-diffusion-2-1"
    ).split(",") if m.strip()
]
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")

def _auth_headers():
    headers = {
        "Accept": "image/png",
        "Content-Type": "application/json",
    }
    if HF_API_TOKEN:
        headers["Authorization"] = f"Bearer {HF_API_TOKEN}"
    return headers

async def _try_generate(session: aiohttp.ClientSession, model: str, prompt: str, width: int, height: int, steps: int, timeout: int) -> Optional[bytes]:
    url = f"{HF_API_URL}/{model}"
    payload = {
        "inputs": prompt,
        "parameters": {"width": width, "height": height, "num_inference_steps": steps},
        "options": {"wait_for_model": True},
    }
    async with session.post(url, headers=_auth_headers(), json=payload, timeout=timeout) as resp:
        if resp.status == 200:
            return await resp.read()
        # 503 often means model is loading; 404/410 often means not available on serverless for this repo
        text = await resp.text()
        logger.warning("HF image gen failed for %s: %s %s", model, resp.status, text[:200])
        if resp.status in (404, 410):
            return None  # switch model
        if resp.status in (429, 500, 502, 503, 504):
            raise RuntimeError(f"HF transient error {resp.status}: {text[:200]}")
        raise RuntimeError(f"HF nonsuccess {resp.status}: {text[:200]}")

async def generate_image_with_fallback(
    prompt: str,
    width: int = 720,
    height: int = 1280,
    steps: int = 25,
    per_attempt_timeout: int = 120,
    max_retries_per_model: int = 2,
    models: Optional[List[str]] = None,
) -> bytes:
    """
    Generate an image via Hugging Face serverless Inference API with model fallback and basic retries.
    Returns raw PNG bytes on success. Raises an Exception if all models fail.
    """
    models = models or HF_IMAGE_MODELS
    if not models:
        raise ValueError("No models configured for HF image generation")

    timeout = aiohttp.ClientTimeout(total=per_attempt_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        last_err: Optional[Exception] = None
        for model in models:
            for attempt in range(1, max_retries_per_model + 1):
                try:
                    img = await _try_generate(session, model, prompt, width, height, steps, timeout)
                    if img is not None:
                        logger.info("HF image gen succeeded with model=%s on attempt %d", model, attempt)
                        return img
                    else:
                        logger.info("Model %s not available (404/410). Trying next model.", model)
                        break  # go to next model
                except RuntimeError as e:
                    last_err = e
                    # backoff before retrying same model
                    await asyncio.sleep(min(3 * attempt, 8))
                    continue
        raise RuntimeError(f"All HF models failed. Last error: {last_err}")
