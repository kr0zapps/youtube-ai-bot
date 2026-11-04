"""Módulo de gestión de gameplay footage para fondos de video.

Busca clips de gameplay locales (Minecraft, Subway Surfers, etc.) en assets/gameplay/
y los prepara para usar como fondo del video en lugar de imágenes estáticas.

El resultado es mucho más viral: historia narrada sobre gameplay en movimiento.
"""

import os
import random
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

GAMEPLAY_DIR = os.path.join("assets", "gameplay")

# Extensiones de video soportadas
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def get_dopamine_2x2_clips() -> list[str]:
    """Devuelve los 4 clips de gameplay para la composición 2x2 Full Dopamina:
    1. Subway Surfers
    2. Minecraft Parkour
    3. GTA 5 Mega Ramp
    4. CS Surf / Parkour
    """
    if not os.path.isdir(GAMEPLAY_DIR):
        return []

    preferred = ["subway_surfers.mp4", "minecraft_parkour.mp4", "gta5_mega_ramp.mp4", "cs_surf.mp4"]
    found = []
    for fname in preferred:
        p = os.path.join(GAMEPLAY_DIR, fname)
        if os.path.exists(p):
            found.append(p)

    if len(found) >= 4:
        return found[:4]

    # Fallback con cualquier video disponible
    all_clips = [
        os.path.join(GAMEPLAY_DIR, f)
        for f in os.listdir(GAMEPLAY_DIR)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
    ]
    return all_clips


def get_random_gameplay_clip() -> Optional[str]:
    """Devuelve la ruta de un clip de gameplay aleatorio de assets/gameplay/.
    
    Returns:
        Ruta al clip, o None si no hay clips disponibles.
    """
    if not os.path.isdir(GAMEPLAY_DIR):
        os.makedirs(GAMEPLAY_DIR, exist_ok=True)
        logger.info("Carpeta assets/gameplay/ creada. Agrega clips MP4 de gameplay ahí.")
        return None

    clips = [
        os.path.join(GAMEPLAY_DIR, f)
        for f in os.listdir(GAMEPLAY_DIR)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
    ]

    if not clips:
        logger.warning(
            "No hay clips de gameplay en assets/gameplay/. "
            "Agrega MP4s de Minecraft, Subway Surfers, etc. para usar este modo."
        )
        return None

    chosen = random.choice(clips)
    logger.info("Clip de gameplay seleccionado: %s", os.path.basename(chosen))
    return chosen


def get_gameplay_duration(clip_path: str, ffmpeg_bin: str) -> float:
    """Obtiene la duración en segundos de un clip de video."""
    import re
    cmd = [ffmpeg_bin, "-i", clip_path]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
        if match:
            h, m, s = match.groups()
            return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception as e:
        logger.warning("No se pudo obtener duración del clip: %s", e)
    return 0.0


def prepare_gameplay_segment(
    clip_path: str,
    audio_duration: float,
    output_path: str,
    ffmpeg_bin: str,
    width: int = 1080,
    height: int = 1920,
) -> str:
    """Recorta y escala un clip de gameplay al tamaño y duración requeridos.

    - Si el clip es más corto que el audio, lo loopea.
    - Aplica crop inteligente para formato vertical 9:16.
    - Oscurece ligeramente para que los subtítulos se lean mejor.

    Args:
        clip_path: Ruta al clip de gameplay original.
        audio_duration: Duración del audio en segundos.
        output_path: Ruta de salida del clip preparado.
        ffmpeg_bin: Ruta al ejecutable de FFmpeg.
        width: Ancho del video de salida (default 1080).
        height: Alto del video de salida (default 1920).

    Returns:
        Ruta del clip preparado.
    """
    clip_duration = get_gameplay_duration(clip_path, ffmpeg_bin)
    logger.info(
        "Preparando gameplay: %.1fs disponibles, %.1fs necesarios",
        clip_duration, audio_duration,
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Punto de inicio aleatorio si el clip es más largo que lo necesario
    start_time = 0.0
    if clip_duration > audio_duration + 10:
        max_start = clip_duration - audio_duration - 5
        start_time = random.uniform(0, max_start)
        logger.info("Iniciando gameplay desde t=%.1fs", start_time)

    # Filtro de video: escalar a 9:16 con crop inteligente + oscurecer 20%
    # Para formato horizontal (16:9) → crop central vertical
    # Para ya vertical → solo escalar
    vf = (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"eq=brightness=-0.08:saturation=0.9"  # Ligeramente oscuro para legibilidad
    )

    # Construir comando FFmpeg
    input_args = ["-ss", f"{start_time:.2f}", "-i", clip_path]

    # Si necesita loop (clip más corto que el audio)
    needs_loop = clip_duration > 0 and clip_duration < audio_duration
    if needs_loop:
        input_args = ["-stream_loop", "-1", "-ss", f"{start_time:.2f}", "-i", clip_path]
        logger.info("Activando loop de gameplay (clip corto)")

    cmd = [
        ffmpeg_bin, "-y",
        *input_args,
        "-vf", vf,
        "-t", f"{audio_duration:.2f}",
        "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",  # Sin audio del gameplay
        output_path,
    ]

    logger.info("Procesando clip de gameplay...")
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )

    if proc.returncode != 0:
        logger.error("Error preparando gameplay: %s", proc.stderr[-400:])
        raise RuntimeError(f"Fallo al preparar clip de gameplay: {proc.stderr[-200:]}")

    logger.info("Gameplay listo: %s (%.1fs)", output_path, audio_duration)
    return output_path
