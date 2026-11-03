"""Módulo de subida y distribución a TikTok.

Soporta dos métodos de publicación:
1. API Oficial de TikTok (Content Posting API v2) mediante TIKTOK_ACCESS_TOKEN.
2. Subida mediante sesión web / cookies de TikTok Creator Center.

Si no hay credenciales configuradas, almacena el video en output/tiktok/ listo para publicar.
"""

import os
import json
import logging
from typing import Optional, List
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


def is_tiktok_configured() -> bool:
    """Verifica si TikTok está configurado en .env o existe archivo de cookies."""
    if os.getenv("TIKTOK_ACCESS_TOKEN"):
        return True
    if os.getenv("TIKTOK_SESSION_ID"):
        return True
    if os.path.exists("tiktok_cookies.txt"):
        return True
    return False


def upload_to_tiktok(
    video_path: str,
    title: str,
    tags: Optional[List[str]] = None,
    privacy_level: str = "PUBLIC_TO_EVERYONE",  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY
) -> bool:
    """Publica un video vertical en TikTok.

    Args:
        video_path: Ruta al archivo MP4 generado.
        title: Título y descripción del video (hasta 2200 caracteres).
        tags: Lista de hashtags opcionales.
        privacy_level: Nivel de privacidad en TikTok.

    Returns:
        True si la subida fue exitosa.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video no encontrado: {video_path}")

    # Formatear título con hashtags para TikTok
    tag_str = " ".join([f"#{t.strip('#')}" for t in (tags or ["fyp", "parati", "misterio", "viral"])])
    full_caption = f"{title}\n\n{tag_str}".strip()[:2000]

    access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
    session_id = os.getenv("TIKTOK_SESSION_ID")

    # ── Método 1: API Oficial de TikTok (Content Posting API v2) ─────────────
    if access_token:
        logger.info("Iniciando subida a TikTok vía Content Posting API Oficial...")
        try:
            return _upload_via_official_api(video_path, full_caption, access_token, privacy_level)
        except Exception as exc:
            logger.error("Error en API oficial de TikTok: %s", exc)

    # ── Método 2: Subida por cookies (tiktok-uploader / sessionid) ────────────
    if session_id or os.path.exists("tiktok_cookies.txt"):
        logger.info("Iniciando subida a TikTok vía sesión web / Creator Center...")
        try:
            return _upload_via_cookies(video_path, full_caption)
        except Exception as exc:
            logger.error("Error en subida por cookies a TikTok: %s", exc)

    # ── Fallback: Guardar copia en output/tiktok/ ─────────────────────────────
    tiktok_out_dir = os.path.join("output", "tiktok")
    os.makedirs(tiktok_out_dir, exist_ok=True)
    out_copy = os.path.join(tiktok_out_dir, os.path.basename(video_path))
    import shutil
    shutil.copy2(video_path, out_copy)

    # Guardar metadata para publicación manual rápida
    meta_path = out_copy.replace(".mp4", "_info.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"TÍTULO Y HASHTAGS TIKTOK:\n{full_caption}\n\nARCHIVO: {out_copy}\n")

    logger.info("Video preparado para TikTok en: %s", out_copy)
    logger.info("Copia el texto de %s al publicar en TikTok.", meta_path)
    return False


def _upload_via_official_api(
    video_path: str,
    caption: str,
    access_token: str,
    privacy_level: str,
) -> bool:
    """Sube el video usando la API Oficial de TikTok v2."""
    file_size = os.path.getsize(video_path)

    # Paso 1: Inicializar publicación
    init_url = f"{TIKTOK_API_BASE}/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    payload = {
        "post_info": {
            "title": caption[:150],
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_stitch": False,
            "disable_comment": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        },
    }

    r = requests.post(init_url, json=payload, headers=headers, timeout=30)
    data = r.json()

    if data.get("error", {}).get("code") != "ok":
        logger.error("Error inicializando subida a TikTok: %s", data)
        return False

    upload_url = data["data"]["upload_url"]
    publish_id = data["data"]["publish_id"]

    # Paso 2: Subir archivo de video
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    upload_headers = {
        "Content-Type": "video/mp4",
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
    }
    up_r = requests.put(upload_url, data=video_bytes, headers=upload_headers, timeout=120)

    if up_r.status_code in (200, 201):
        logger.info("✓ Video publicado con éxito en TikTok! Publish ID: %s", publish_id)
        return True

    logger.error("Error transfiriendo video a TikTok: status %d", up_r.status_code)
    return False


def _upload_via_cookies(video_path: str, caption: str) -> bool:
    """Sube video a TikTok Creator Center usando cookies de sesión."""
    try:
        from tiktok_uploader.upload import upload_video
        cookie_file = "tiktok_cookies.txt"
        success = upload_video(
            filename=video_path,
            description=caption,
            cookies=cookie_file,
        )
        if success:
            logger.info("✓ Video publicado en TikTok vía Creator Center.")
            return True
    except ImportError:
        logger.warning("tiktok-uploader no instalado. Instalar con: pip install tiktok-uploader")
    except Exception as e:
        logger.warning("Fallo en subida por cookies: %s", e)
    return False
