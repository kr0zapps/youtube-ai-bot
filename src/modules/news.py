"""Módulo de Noticias y Curiosidades del Día.

Pipeline automatizado que:
1. Extrae noticias de fuentes RSS confiables en español (El País, RTVE, BBC Mundo).
2. Selecciona la noticia más atractiva y genera un resumen viral con Gemini.
3. Sintetiza la locución con Edge-TTS (voz Elvira clara y profesional).
4. Diseña imágenes estilo foto-periodismo y tecnología con Pollinations.ai.
5. Construye subtítulos dinámicos de alto impacto visual.
6. Ensambla el Short con efecto Ken Burns y música de actualidad.
7. Sube el resultado a YouTube.
"""

import os
import re
import html
import yaml
import shutil
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import feedparser

from src.core import gemini, voice, images, subtitles, video, uploader
from src.core import gameplay as gameplay_module

logger = logging.getLogger(__name__)

# Feeds RSS oficiales en español
DEFAULT_RSS_FEEDS = [
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "https://www.rtve.es/api/noticias.rss",
    "https://www.bbc.com/mundo/index.xml",
]


def _clean_html_text(raw_html: str) -> str:
    """Limpia etiquetas HTML y entidades de texto."""
    if not raw_html:
        return ""
    # Quitar tags HTML
    text = re.sub(r"<[^>]+>", " ", raw_html)
    # Decodificar entidades (&amp;, &quot;, etc.)
    text = html.unescape(text)
    # Normalizar espacios
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_latest_news(feed_urls: Optional[List[str]] = None) -> Dict[str, str]:
    """Obtiene la noticia más reciente y relevante de los feeds RSS.

    Returns:
        Dict con {"title": str, "summary": str, "source": str, "formatted": str}
    """
    urls = feed_urls or DEFAULT_RSS_FEEDS
    candidates = []

    for url in urls:
        logger.info("Consultando feed RSS: %s", url)
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue

            for entry in feed.entries[:5]:  # Tomar las 5 más recientes de cada fuente
                title = _clean_html_text(getattr(entry, "title", ""))
                summary = _clean_html_text(getattr(entry, "summary", "") or getattr(entry, "description", ""))

                if len(title) > 15 and len(summary) > 40:
                    candidates.append({
                        "title": title,
                        "summary": summary,
                        "source": getattr(feed.feed, "title", "Noticias"),
                    })
        except Exception as exc:
            logger.warning("Error leyendo feed %s: %s", url, exc)

    if not candidates:
        logger.warning("No se pudieron obtener noticias en vivo de los feeds RSS. Usando noticia destacada de respaldo.")
        return {
            "title": "Avance histórico en energía de fusión nuclear",
            "summary": "Científicos logran por primera vez una reacción neta de fusión que genera más energía de la que consume el proceso, abriendo las puertas a una era de energía limpia e inagotable.",
            "source": "Ciencia Global",
            "formatted": "Título: Avance histórico en energía de fusión nuclear\nDetalles: Científicos logran una reacción neta de fusión comercial prometedora.",
        }

    # Seleccionar la candidata con mayor nivel de detalle
    chosen = sorted(candidates, key=lambda c: len(c["summary"]), reverse=True)[0]
    chosen["formatted"] = f"Titular: {chosen['title']}\nResumen: {chosen['summary']}\nFuente: {chosen['source']}"
    logger.info("Noticia seleccionada: '%s' (%s)", chosen["title"], chosen["source"])
    return chosen


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
    """Ejecuta el pipeline completo del módulo de Noticias y Curiosidades.

    Args:
        config: Configuración global cargada de config.yaml.
        output_dir: Carpeta de salida (default: output/news).
        dry_run: Si es True, no sube a YouTube y mantiene archivos intermedios.
        no_upload: Si es True, salta el paso de subida a YouTube.

    Returns:
        Ruta del archivo de video MP4 final.
    """
    cfg = _load_config(config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Carpetas de trabajo
    base_output = output_dir or os.path.join("output", "news")
    work_dir = os.path.join(base_output, f"temp_{timestamp}")
    final_video_name = f"news_{timestamp}.mp4"
    final_video_path = os.path.join(base_output, final_video_name)

    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(base_output, exist_ok=True)

    logger.info("=== INICIANDO PIPELINE: NOTICIAS Y CURIOSIDADES [%s] ===", timestamp)

    try:
        # Paso 1: Obtener noticia de los feeds RSS
        logger.info("[1/7] Extrayendo noticia más destacada de feeds RSS...")
        news_item = fetch_latest_news()

        # Paso 2: Generar guión con Gemini
        logger.info("[2/7] Generando guión viral de noticias con Gemini...")
        model_name = cfg.get("gemini", {}).get("model", "gemini-2.0-flash-lite")
        temperature = cfg.get("gemini", {}).get("temperature", 0.9)
        max_tokens = cfg.get("gemini", {}).get("max_output_tokens", 1024)

        script_data = gemini.generate_script(
            module_type="news",
            extra_context=news_item["formatted"],
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        script_text = script_data["script"]
        video_title = script_data["title"]

        with open(os.path.join(work_dir, "script.txt"), "w", encoding="utf-8") as f:
            f.write(f"Titular original: {news_item['title']}\n")
            f.write(f"Título Short: {video_title}\n\nGuión:\n{script_text}\n")

        # Paso 3: Síntesis de voz con Edge-TTS
        logger.info("[3/7] Sintetizando voz informativa con Edge-TTS...")
        voice_name = cfg.get("voice", {}).get("voice_news", "es-ES-ElviraNeural")
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
                module_type="news",
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
                f"Fuente de referencia: {news_item['title']}\n\n"
                "#Shorts #Noticias #Actualidad #Curiosidades #SabiasQue #Tendencias"
            )
            tags = [
                "Shorts",
                "Noticias",
                "Actualidad",
                "Curiosidades",
                "Sabías que",
                "Mundo",
                "Tendencias",
            ]
            try:
                uploader.upload_video(
                    video_path=final_video_path,
                    title=video_title,
                    description=description,
                    tags=tags,
                    category_id="25",  # News & Politics
                )
            except Exception as up_exc:
                logger.error("Error al subir a YouTube: %s. El video final se preserva.", up_exc)

        # Paso 8: Distribución a TikTok
        from src.core import tiktok as tiktok_module
        try:
            tiktok_tags = ["fyp", "parati", "noticias", "curiosidades", "sabiasque"]
            tiktok_module.upload_to_tiktok(
                video_path=final_video_path,
                title=video_title,
                tags=tiktok_tags,
            )
        except Exception as tk_exc:
            logger.warning("Aviso TikTok: %s", tk_exc)

        # Limpieza de archivos temporales
        if not dry_run and os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir)
                logger.info("Carpeta temporal limpiada: %s", work_dir)
            except Exception as rm_exc:
                logger.warning("No se pudo eliminar la carpeta temporal %s: %s", work_dir, rm_exc)

        logger.info("=== PIPELINE NOTICIAS FINALIZADO CON ÉXITO ===")
        logger.info("Video final disponible en: %s", final_video_path)
        return final_video_path

    except Exception as exc:
        logger.error("Error crítico en el pipeline de Noticias: %s", exc, exc_info=True)
        raise RuntimeError(f"Fallo en ejecución del módulo Noticias: {exc}") from exc
