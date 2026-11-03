"""Módulo de generación de imágenes usando múltiples APIs gratuitas.

Orden de intentos:
1. Pollinations.ai (gen.pollinations.ai) — AI Flux, timeout=75s, retry con backoff
2. AI Horde (stablehorde.net) — SDXL gratis, clave anónima "0000000000"
3. Picsum Photos — fotos random HD, fallback rápido
4. Color degradado — fallback final, siempre funciona
"""

import os
import io
import re
import time
import random
import hashlib
import logging
import urllib.parse
from typing import List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

POLLINATIONS_NEW_URL = "https://image.pollinations.ai/prompt"
HORDE_API_URL = "https://stablehorde.net/api/v2"
HORDE_ANON_KEY = "0000000000"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    """Crea una sesión requests con reintentos automáticos para errores de red."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[500, 502, 503, 504, 429],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _save_image_data(data: bytes, output_path: str, width: int, height: int) -> bool:
    """Guarda y redimensiona datos de imagen. Retorna True si fue exitoso."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img_ratio = img.width / img.height
        target_ratio = width / height
        if img_ratio > target_ratio:
            new_h = height
            new_w = int(new_h * img_ratio)
        else:
            new_w = width
            new_h = int(new_w / img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        img = img.crop((left, top, left + width, top + height))
        img.save(output_path, "JPEG", quality=92)
        return True
    except Exception as e:
        logger.debug("Error guardando imagen: %s", e)
        return False


def _create_fallback_image(output_path: str, width: int = 1080, height: int = 1920) -> str:
    """Crea una imagen de respaldo con degradado único según la ruta."""
    palettes = [
        ((10, 5, 25), (50, 15, 90)),
        ((5, 15, 30), (10, 50, 100)),
        ((25, 5, 5), (90, 20, 20)),
        ((5, 20, 10), (15, 70, 30)),
        ((20, 15, 5), (80, 55, 10)),
        ((5, 5, 25), (20, 20, 80)),
    ]
    idx = int(hashlib.md5(output_path.encode()).hexdigest(), 16) % len(palettes)
    top_color, bottom_color = palettes[idx]
    img = Image.new("RGB", (width, height), color=top_color)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    img.save(output_path, "JPEG", quality=90)
    logger.info("Fallback color #%d: %s", idx + 1, output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# API 1: Pollinations.ai (nueva URL + timeout largo + backoff)
# ──────────────────────────────────────────────────────────────────────────────

def _try_pollinations(prompt: str, width: int, height: int) -> Optional[bytes]:
    """Pollinations.ai con timeout=75s y hasta 3 intentos con backoff."""
    session = _make_session()
    encoded = urllib.parse.quote(prompt.strip()[:500])
    seed = random.randint(1, 9999999)
    url = (
        f"{POLLINATIONS_NEW_URL}/{encoded}"
        f"?width={width}&height={height}&nologo=true&seed={seed}&enhance=true"
    )
    for attempt in range(1, 4):
        try:
            r = session.get(
                url, timeout=75,
                headers={"User-Agent": "Mozilla/5.0 YouTubeAIBot/1.0"},
            )
            if r.status_code == 200 and len(r.content) > 5000:
                logger.debug("Pollinations OK (intento %d, %d bytes)", attempt, len(r.content))
                return r.content
            logger.debug("Pollinations intento %d: status=%d, bytes=%d", attempt, r.status_code, len(r.content))
        except requests.Timeout:
            logger.debug("Pollinations timeout en intento %d", attempt)
        except Exception as e:
            logger.debug("Pollinations error intento %d: %s", attempt, e)
        if attempt < 3:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# API 2: AI Horde (SDXL gratis, clave anónima, async polling)
# ──────────────────────────────────────────────────────────────────────────────

def _try_ai_horde(prompt: str, width: int, height: int, max_wait: int = 120) -> Optional[bytes]:
    """AI Horde: genera imagen con SDXL usando clave anónima gratuita.
    
    Envía la solicitud y hace polling hasta que la imagen esté lista.
    Tiempo de espera máximo: max_wait segundos.
    """
    # Ajustar dimensiones a múltiplos de 64 que soporte SDXL
    # AI Horde soporta hasta 1024x1024 para SDXL
    horde_w = min(768, (width // 64) * 64)
    horde_h = min(1024, (height // 64) * 64)

    headers = {
        "Content-Type": "application/json",
        "apikey": HORDE_ANON_KEY,
        "Client-Agent": "YouTubeAIBot:1.0:github.com",
    }
    payload = {
        "prompt": prompt[:500],
        "params": {
            "width": horde_w,
            "height": horde_h,
            "steps": 20,
            "sampler_name": "k_euler",
            "n": 1,
        },
        "nsfw": False,
        "models": ["stable_diffusion"],
        "r2": True,
    }

    try:
        # Enviar solicitud
        r = requests.post(
            f"{HORDE_API_URL}/generate/async",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if r.status_code not in (200, 202):
            logger.debug("AI Horde submit error: %d %s", r.status_code, r.text[:200])
            return None

        job_id = r.json().get("id")
        if not job_id:
            logger.debug("AI Horde: no se recibió job_id")
            return None

        logger.info("AI Horde: job %s enviado, esperando imagen...", job_id)

        # Polling hasta que esté listo
        elapsed = 0
        while elapsed < max_wait:
            time.sleep(8)
            elapsed += 8
            check = requests.get(
                f"{HORDE_API_URL}/generate/check/{job_id}",
                timeout=15,
            ).json()
            done = check.get("done", False)
            queue_pos = check.get("queue_position", "?")
            logger.debug("AI Horde: done=%s, queue=%s, t=%ds", done, queue_pos, elapsed)

            if done:
                status = requests.get(
                    f"{HORDE_API_URL}/generate/status/{job_id}",
                    timeout=30,
                ).json()
                gens = status.get("generations", [])
                if gens:
                    img_url = gens[0].get("img")
                    if img_url:
                        img_r = requests.get(img_url, timeout=30)
                        if img_r.status_code == 200 and len(img_r.content) > 1000:
                            logger.info("✓ AI Horde OK (%d bytes)", len(img_r.content))
                            return img_r.content
                logger.debug("AI Horde: done pero sin imagen válida")
                return None

        logger.warning("AI Horde: timeout (%ds) esperando imagen", max_wait)
        return None

    except Exception as e:
        logger.debug("AI Horde error: %s", e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# API 3: Picsum (fotos aleatorias HD, muy confiable)
# ──────────────────────────────────────────────────────────────────────────────

def _try_picsum(seed_str: str, width: int, height: int) -> Optional[bytes]:
    """Descarga imagen aleatoria HD desde Lorem Picsum."""
    seed = abs(hash(seed_str)) % 1000
    url = f"https://picsum.photos/seed/{seed}/{min(width, 1920)}/{min(height, 1920)}"
    try:
        r = requests.get(url, timeout=15, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 YouTubeAIBot/1.0"})
        if r.status_code == 200 and len(r.content) > 5000:
            return r.content
    except Exception as e:
        logger.debug("Picsum error: %s", e)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Función principal
# ──────────────────────────────────────────────────────────────────────────────

def generate_single_image(
    prompt: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    use_horde: bool = False,
) -> str:
    """Genera una imagen con fallback automático entre APIs.
    
    Orden: Pollinations → (AI Horde si use_horde) → Picsum → degradado
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) if os.path.dirname(output_path) else ".", exist_ok=True)
    logger.info("Generando imagen: '%s'...", prompt[:70])

    # 1. Pollinations (nuevo endpoint, timeout largo, retry)
    data = _try_pollinations(prompt, width, height)
    if data and _save_image_data(data, output_path, width, height):
        logger.info("✓ Pollinations OK: %s", output_path)
        return output_path

    # 2. AI Horde (SDXL gratis, más lento)
    if use_horde:
        data = _try_ai_horde(prompt, width, height)
        if data and _save_image_data(data, output_path, width, height):
            logger.info("✓ AI Horde OK: %s", output_path)
            return output_path

    # 3. Picsum (aleatorio pero HD, siempre funciona)
    data = _try_picsum(seed_str=output_path, width=width, height=height)
    if data and _save_image_data(data, output_path, width, height):
        logger.info("✓ Picsum OK: %s", output_path)
        return output_path

    # 4. Degradado de color
    logger.warning("Todas las APIs fallaron. Usando fallback de color.")
    return _create_fallback_image(output_path, width, height)


def generate_images(
    descriptions: List[str],
    output_dir: str,
    width: int = 1080,
    height: int = 1920,
    use_horde: bool = False,
) -> List[str]:
    """Genera una colección de imágenes en paralelo con fallback automático."""
    if not descriptions:
        raise ValueError("La lista de descripciones no puede estar vacía.")

    os.makedirs(output_dir, exist_ok=True)
    image_paths: List[str] = []

    logger.info("Iniciando generación de %d imágenes...", len(descriptions))

    for idx, desc in enumerate(descriptions, start=1):
        filename = f"image_{idx:02d}.jpg"
        target_path = os.path.join(output_dir, filename)
        try:
            saved = generate_single_image(
                prompt=desc,
                output_path=target_path,
                width=width,
                height=height,
                use_horde=use_horde,
            )
            image_paths.append(saved)
        except Exception as exc:
            logger.error("Error generando imagen %d: %s", idx, exc)
            image_paths.append(_create_fallback_image(target_path, width, height))

        if idx < len(descriptions):
            time.sleep(1)

    logger.info("Generación completada: %d imágenes.", len(image_paths))
    return image_paths
