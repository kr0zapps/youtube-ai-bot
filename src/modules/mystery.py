"""Módulo de Historias de Misterio y Terror.

Pipeline automatizado que:
1. Genera guiones de historias de terror y misterio con giros inesperados usando Gemini.
2. Sintetiza la locución con Edge-TTS (voz Álvaro dramática).
3. Crea imágenes oscuras y cinematográficas con Pollinations.ai.
4. Construye subtítulos dinámicos de alto impacto visual.
5. Ensambla el Short con efecto Ken Burns y música de suspenso.
6. Sube el resultado a YouTube.
"""

import os
import yaml
import shutil
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from src.core import gemini, voice, images, subtitles, video, uploader
from src.core import gameplay as gameplay_module

logger = logging.getLogger(__name__)


def _load_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Carga config.yaml si no se proporciona un diccionario."""
    if config:
        return config
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def run(
    config: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
    dry_run: bool = False,
    no_upload: bool = False,
) -> str:
    """Ejecuta el pipeline completo del módulo de Misterio y Terror.

    Args:
        config: Configuración global cargada de config.yaml.
        output_dir: Carpeta de salida (default: output/mystery).
        dry_run: Si es True, no sube a YouTube y mantiene archivos intermedios.
        no_upload: Si es True, salta el paso de subida a YouTube.

    Returns:
        Ruta del archivo de video MP4 final.
    """
    cfg = _load_config(config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Carpetas de trabajo
    base_output = output_dir or os.path.join("output", "mystery")
    work_dir = os.path.join(base_output, f"temp_{timestamp}")
    final_video_name = f"mystery_{timestamp}.mp4"
    final_video_path = os.path.join(base_output, final_video_name)

    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(base_output, exist_ok=True)

    logger.info("=== INICIANDO PIPELINE: MISTERIO Y TERROR [%s] ===", timestamp)

    try:
        # Paso 1: Generación de guión con Gemini
        logger.info("[1/6] Generando guión de misterio con Gemini...")
        model_name = cfg.get("gemini", {}).get("model", "gemini-2.0-flash-lite")
        temperature = cfg.get("gemini", {}).get("temperature", 0.9)
        max_tokens = cfg.get("gemini", {}).get("max_output_tokens", 1024)

        script_data = gemini.generate_script(
            module_type="mystery",
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        script_text = script_data["script"]
        video_title = script_data["title"]

        # Guardar copia del guión en work_dir
        with open(os.path.join(work_dir, "script.txt"), "w", encoding="utf-8") as f:
            f.write(f"Título: {video_title}\n\nGuión:\n{script_text}\n")

        # Paso 2: Síntesis de voz con Edge-TTS
        logger.info("[2/6] Sintetizando voz con Edge-TTS...")
        voice_name = cfg.get("voice", {}).get("voice_mystery", "es-ES-AlvaroNeural")
        audio_path = os.path.join(work_dir, "voice.mp3")

        word_timings = asyncio.run(
            voice.generate_voice(
                text=script_text,
                output_path=audio_path,
                voice_name=voice_name,
            )
        )

        # Paso 3: Generación de imágenes o selección de gameplay
        logger.info("[3/6] Diseñando y descargando imágenes atmosféricas...")

        # ¿Hay gameplay disponible? → usarlo en lugar de imágenes
        gameplay_clip = gameplay_module.get_random_gameplay_clip()
        if gameplay_clip:
            logger.info("✓ Modo GAMEPLAY activo: %s", os.path.basename(gameplay_clip))
            image_paths = []
        else:
            # Sin gameplay → generar imágenes con IA
            img_prompts = gemini.generate_image_prompts(
                script=script_text,
                module_type="mystery",
                num_images=9,
            )
            images_dir = os.path.join(work_dir, "images")
            image_paths = images.generate_images(img_prompts, images_dir)

        # Paso 4: Creación de subtítulos animados (.ass)
        logger.info("[4/6] Construyendo subtítulos karaoke en formato ASS...")
        sub_path = os.path.join(work_dir, "subtitles.ass")
        words_per_line = cfg.get("subtitles", {}).get("words_per_subtitle", 3)
        subtitles.generate_subtitles(
            word_timings=word_timings,
            output_path=sub_path,
            words_per_line=words_per_line,
            config=cfg,
        )

        # Paso 5: Ensamble del video con FFmpeg
        logger.info("[5/6] Ensamblando video con FFmpeg (Ken Burns, música y subtítulos)...")
        music_path = os.path.join("assets", "music", "mystery_bg.mp3")
        if not os.path.exists(music_path):
            music_path = None

        video.assemble_video(
            image_paths=image_paths,
            audio_path=audio_path,
            subtitle_path=sub_path,
            music_path=music_path,
            output_path=final_video_path,
            config=cfg,
            gameplay_path=gameplay_clip if gameplay_clip else None,
        )

        # Paso 6: Subida a YouTube
        if dry_run or no_upload:
            logger.info("[6/6] Modo DRY-RUN o NO-UPLOAD activo: saltando subida a YouTube.")
        else:
            logger.info("[6/6] Subiendo Short a YouTube...")
            description = (
                f"{script_text}\n\n"
                "#Shorts #Misterio #Terror #HistoriasDeTerror #Paranormal #Suspense #Creepypasta"
            )
            tags = [
                "Shorts",
                "Misterio",
                "Terror",
                "Historias de terror",
                "Paranormal",
                "Suspense",
                "Creepypasta",
            ]
            try:
                uploader.upload_video(
                    video_path=final_video_path,
                    title=video_title,
                    description=description,
                    tags=tags,
                    category_id="24",  # Entertainment
                )
            except Exception as up_exc:
                logger.error("Error al subir a YouTube: %s. El video final se preserva.", up_exc)

        # Limpieza de archivos temporales de trabajo si no es dry_run
        if not dry_run and os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir)
                logger.info("Carpeta temporal limpiada: %s", work_dir)
            except Exception as rm_exc:
                logger.warning("No se pudo eliminar la carpeta temporal %s: %s", work_dir, rm_exc)

        logger.info("=== PIPELINE MISTERIO FINALIZADO CON ÉXITO ===")
        logger.info("Video final disponible en: %s", final_video_path)
        return final_video_path

    except Exception as exc:
        logger.error("Error crítico en el pipeline de Misterio: %s", exc, exc_info=True)
        raise RuntimeError(f"Fallo en ejecución del módulo Misterio: {exc}") from exc
