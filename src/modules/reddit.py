"""Módulo de Reddit Stories.

Pipeline automatizado que:
1. Conecta con Reddit mediante PRAW (o historias destacadas de respaldo).
2. Selecciona historias virales con alto engagement en r/historias, r/AskReddit, r/tifu.
3. Adapta la historia a formato narrativo en primera persona usando Gemini.
4. Sintetiza la locución con Edge-TTS (voz Jorge casual latinoamericano).
5. Crea imágenes cinemáticas y cotidianas con Pollinations.ai.
6. Construye subtítulos dinámicos de alto impacto visual.
7. Ensambla el Short con efecto Ken Burns y música ambiental.
8. Sube el resultado a YouTube.
"""

import os
import yaml
import shutil
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from src.core import gemini, voice, images, subtitles, video, uploader
from src.core import gameplay as gameplay_module

load_dotenv()
logger = logging.getLogger(__name__)

# Subreddits recomendados (en español e internacionales con historias ricas)
TARGET_SUBREDDITS = ["historias", "tifu", "AskReddit"]


def fetch_top_reddit_story() -> Dict[str, str]:
    """Obtiene la historia más votada del día de Reddit usando PRAW.

    Si las credenciales no están configuradas o la red falla,
    retorna una historia viral clásica de respaldo.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "youtube-ai-bot/1.0")

    if not client_id or client_id == "tu_client_id" or not client_secret:
        logger.warning(
            "Credenciales de Reddit no configuradas en .env. Usando historia viral destacada de archivo."
        )
        return _get_fallback_story()

    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        candidates = []

        for sub_name in TARGET_SUBREDDITS:
            logger.info("Explorando subreddit: r/%s...", sub_name)
            subreddit = reddit.subreddit(sub_name)

            # Obtener los mejores posts del día
            for post in subreddit.top(time_filter="day", limit=10):
                # Filtrar posts que contengan texto (no solo links o imágenes)
                body = post.selftext.strip() if hasattr(post, "selftext") else ""
                title = post.title.strip() if hasattr(post, "title") else ""

                if post.score >= 500 and len(body) >= 120 and not post.over_18:
                    candidates.append({
                        "title": title,
                        "text": body,
                        "score": post.score,
                        "subreddit": sub_name,
                    })

            if candidates:
                break

        # Si ninguno superó 500, relajar el filtro al post con mejor puntuación
        if not candidates:
            logger.info("Buscando con umbral relajado de upvotes...")
            subreddit = reddit.subreddit(TARGET_SUBREDDITS[0])
            for post in subreddit.hot(limit=10):
                body = post.selftext.strip() if hasattr(post, "selftext") else ""
                if len(body) >= 100:
                    candidates.append({
                        "title": post.title,
                        "text": body,
                        "score": post.score,
                        "subreddit": TARGET_SUBREDDITS[0],
                    })

        if candidates:
            # Ordenar por puntuación
            best_post = sorted(candidates, key=lambda p: p["score"], reverse=True)[0]
            logger.info("Historia de Reddit seleccionada: '%s' (r/%s, %d upvotes)", best_post["title"], best_post["subreddit"], best_post["score"])
            return {
                "title": best_post["title"],
                "text": f"Título: {best_post['title']}\n\nHistoria:\n{best_post['text'][:1500]}",
            }

    except Exception as exc:
        logger.warning("Fallo al conectar con la API de Reddit: %s. Utilizando historia de respaldo.", exc)

    return _get_fallback_story()


def _get_fallback_story() -> Dict[str, str]:
    """Retorna una historia viral de respaldo lista para adaptar."""
    return {
        "title": "El misterioso paquete que llegó a mi puerta por error",
        "text": (
            "Título: Recibí un paquete anónimo que cambió mi vida.\n"
            "Historia: Un martes por la mañana encontré una caja de madera antigua en mi puerta sin remitente. "
            "Dentro había una cámara instantánea de los años 80 y una sola foto ya revelada... "
            "En la foto se veía exactamente la sala de mi casa tomada desde la ventana, con la fecha de mañana escrita en el reverso."
        ),
    }


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
    """Ejecuta el pipeline completo del módulo de Reddit Stories.

    Args:
        config: Configuración global cargada de config.yaml.
        output_dir: Carpeta de salida (default: output/reddit).
        dry_run: Si es True, no sube a YouTube y mantiene archivos intermedios.
        no_upload: Si es True, salta el paso de subida a YouTube.

    Returns:
        Ruta del archivo de video MP4 final.
    """
    cfg = _load_config(config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Carpetas de trabajo
    base_output = output_dir or os.path.join("output", "reddit")
    work_dir = os.path.join(base_output, f"temp_{timestamp}")
    final_video_name = f"reddit_{timestamp}.mp4"
    final_video_path = os.path.join(base_output, final_video_name)

    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(base_output, exist_ok=True)

    logger.info("=== INICIANDO PIPELINE: REDDIT STORIES [%s] ===", timestamp)

    try:
        # Paso 1: Obtener historia de Reddit
        logger.info("[1/7] Obteniendo historia viral de Reddit...")
        reddit_data = fetch_top_reddit_story()

        # Paso 2: Adaptar guión con Gemini
        logger.info("[2/7] Adaptando guión con Gemini a primera persona...")
        model_name = cfg.get("gemini", {}).get("model", "gemini-2.0-flash-lite")
        temperature = cfg.get("gemini", {}).get("temperature", 0.9)
        max_tokens = cfg.get("gemini", {}).get("max_output_tokens", 1024)

        script_data = gemini.generate_script(
            module_type="reddit",
            extra_context=reddit_data["text"],
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        script_text = script_data["script"]
        video_title = script_data["title"]

        with open(os.path.join(work_dir, "script.txt"), "w", encoding="utf-8") as f:
            f.write(f"Post original: {reddit_data['title']}\n")
            f.write(f"Título Short: {video_title}\n\nGuión:\n{script_text}\n")

        # Paso 3: Síntesis de voz con Edge-TTS
        logger.info("[3/7] Sintetizando voz casual con Edge-TTS...")
        voice_name = cfg.get("voice", {}).get("voice_reddit", "es-MX-JorgeNeural")
        audio_path = os.path.join(work_dir, "voice.mp3")

        word_timings = asyncio.run(
            voice.generate_voice(
                text=script_text,
                output_path=audio_path,
                voice_name=voice_name,
            )
        )

        # Paso 4: Generación de imágenes o selección de gameplay
        logger.info("[4/7] Preparando fondo visual...")
        gameplay_clip = gameplay_module.get_random_gameplay_clip()
        if gameplay_clip:
            logger.info("✓ Modo GAMEPLAY activo: %s", os.path.basename(gameplay_clip))
            image_paths = []
        else:
            img_prompts = gemini.generate_image_prompts(
                script=script_text,
                module_type="reddit",
                num_images=6,
            )
            images_dir = os.path.join(work_dir, "images")
            image_paths = images.generate_images(img_prompts, images_dir)

        # Paso 5: Creación de subtítulos animados (.ass)
        logger.info("[5/7] Construyendo subtítulos karaoke en formato ASS...")
        sub_path = os.path.join(work_dir, "subtitles.ass")
        words_per_line = cfg.get("subtitles", {}).get("words_per_subtitle", 3)
        subtitles.generate_subtitles(
            word_timings=word_timings,
            output_path=sub_path,
            words_per_line=words_per_line,
            config=cfg,
        )

        # Paso 6: Ensamble del video con FFmpeg
        logger.info("[6/7] Ensamblando video con FFmpeg...")
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

        # Paso 7: Subida a YouTube
        if dry_run or no_upload:
            logger.info("[7/7] Modo DRY-RUN o NO-UPLOAD activo: saltando subida a YouTube.")
        else:
            logger.info("[7/7] Subiendo Short a YouTube...")
            description = (
                f"{script_text}\n\n"
                "#Shorts #Reddit #RedditStories #HistoriasDeReddit #Confesiones #Viral"
            )
            tags = [
                "Shorts",
                "Reddit",
                "Reddit stories",
                "Historias de Reddit",
                "Historias reales",
                "Confesiones",
                "Storytime",
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

        # Limpieza de archivos temporales
        if not dry_run and os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir)
                logger.info("Carpeta temporal limpiada: %s", work_dir)
            except Exception as rm_exc:
                logger.warning("No se pudo eliminar la carpeta temporal %s: %s", work_dir, rm_exc)

        logger.info("=== PIPELINE REDDIT FINALIZADO CON ÉXITO ===")
        logger.info("Video final disponible en: %s", final_video_path)
        return final_video_path

    except Exception as exc:
        logger.error("Error crítico en el pipeline de Reddit: %s", exc, exc_info=True)
        raise RuntimeError(f"Fallo en ejecución del módulo Reddit: {exc}") from exc
