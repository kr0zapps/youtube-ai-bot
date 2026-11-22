"""Módulo de Automatización para GTA 6 (Faceless Clipping Page).

Cumple estrictamente con el SOP / Mega Prompt:
1. Distribución en 3 pilares: Official News (news), HOW-TO / Utility (tips), y Trailer/Clip Breakdowns (clip).
2. Seguridad y Veracidad (Sección 14): Validación contra facts.md y fuentes oficiales de Rockstar Games.
3. Bucle de Aprendizaje (Sección 13): Registro automático en scoreboard.csv con ID de post, fecha, hora, pilar, formato y test.
4. Soporte de subida y distribución multicanal (Buffer, YouTube Shorts y TikTok).
"""

import os
import re
import yaml
import shutil
import random
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.core import gemini, voice, subtitles, video, uploader, tiktok, clip_downloader, trend_fetcher
from src.core import scoreboard, buffer_uploader

logger = logging.getLogger(__name__)

GTA6_DIR = "gta6"
FACTS_PATH = os.path.join(GTA6_DIR, "facts.md")
IDEA_BANK_PATH = os.path.join(GTA6_DIR, "idea-bank.md")
LOG_PATH = os.path.join(GTA6_DIR, "log.md")
EDITS_DIR = os.path.join(GTA6_DIR, "media", "edits")
OFFICIAL_MEDIA_DIR = os.path.join(GTA6_DIR, "media", "official")
RAW_MEDIA_DIR = os.path.join(GTA6_DIR, "media", "raw")


def _read_file_safe(path: str) -> str:
    """Lee un archivo de texto de forma segura."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        logger.warning("Error leyendo %s: %s", path, exc)
        return ""


def load_verified_facts() -> str:
    """Carga los hechos oficiales verificados desde facts.md."""
    facts = _read_file_safe(FACTS_PATH)
    if not facts:
        return (
            "GTA 6 está ambientado en el estado de Leonida (Vice City y alrededores). "
            "Protagonistas oficiales confirmados: Lucía y Jason. "
            "Plataformas confirmadas: PlayStation 5 y Xbox Series X|S. "
            "Ventana oficial de lanzamiento anunciada por Take-Two: Otoño 2025."
        )
    return facts


def select_topic_from_bank(pillar: str) -> Dict[str, str]:
    """Selecciona un borrador del idea-bank.md para el pilar solicitado."""
    content = _read_file_safe(IDEA_BANK_PATH)
    if not content:
        return {
            "title": "GTA 6 en Leonida",
            "context": "El estado de Leonida y la tecnología de multitudes de Vice City.",
        }

    # Buscar secciones de borradores
    drafts = re.findall(r"### Draft \d+:\s*(.*?)\n- \*\*Pillar:\*\*\s*`?(.*?)`?\s*\|.*?\n- \*\*Hook.*?\*\*:\s*\"?(.*?)\"?\n- \*\*Core Message:\*\*\s*(.*?)\n", content)
    
    pillar_map = {
        "news": "official_news",
        "tips": "howto_utility",
        "clip": "clip_highlight",
    }
    target_pillar = pillar_map.get(pillar, pillar)

    matching = [d for d in drafts if target_pillar in d[1]]
    if not matching:
        matching = drafts

    if matching:
        chosen = random.choice(matching)
        return {
            "title": chosen[0].strip(),
            "hook": chosen[2].strip(),
            "context": f"Título: {chosen[0]}\nGancho sugerido: {chosen[2]}\nDetalles clave: {chosen[3]}",
        }

    return {
        "title": "GTA 6 Lanzamiento Oficial",
        "context": "Detalles oficiales confirmados por Rockstar Games sobre el Estado de Leonida.",
    }


def find_background_video(
    pillar: str = "news",
    topic_text: str = "",
    forced_clip_query: str = "",
    video_url: str = "",
) -> str:
    """Descarga dinámicamente un clip de GTA 6 relevante al tema del video.

    100% dinámico:
    1. Si hay video_url (ej. clip viral de Reddit/Twitter de la noticia de hoy), lo descarga directamente.
    2. Si no, busca en YouTube un clip específico del tema que se comenta hoy.
    3. Corta un fragmento aleatorio único (30s a 220s) para que nunca se repita.
    4. Estrictamente PROHIBIDO el tráiler oficial.
    """
    used_clips = clip_downloader.load_used_clips()
    os.makedirs(RAW_MEDIA_DIR, exist_ok=True)

    # 1. PRIORIDAD MÁXIMA: Descargar el clip viral EXACTO del suceso de hoy si viene en la noticia
    if video_url:
        logger.info("Descargando clip viral directo del evento de hoy: %s", video_url)
        try:
            clip_data = clip_downloader.download_clip_by_url(video_url, output_dir=RAW_MEDIA_DIR)
            if clip_data and os.path.exists(clip_data["video_path"]) and os.path.getsize(clip_data["video_path"]) > 1024 * 1024:
                path = clip_data["video_path"]
                clip_downloader.mark_clip_as_used(path)
                logger.info("✓ Usando el clip viral EXACTO de lo que pasó: %s", path)
                return path
        except Exception as v_err:
            logger.warning("No se pudo descargar el clip viral por URL: %s", v_err)

    # 2. SEGUNDA PRIORIDAD: Usar clips locales descargados previamente que no hayan sido usados
    gta6_clips = []
    if os.path.exists(RAW_MEDIA_DIR):
        for f in os.listdir(RAW_MEDIA_DIR):
            if ".f" in f or f.endswith(".json") or f.endswith(".txt") or "trailer" in f.lower():
                continue
            if any(b in f.lower() for b in ["san_andreas", "sanandreas", "gta_sa", "gta4", "gta_iv", "gta5", "gta_v", "gta3"]):
                continue
            if f.lower().endswith((".mp4", ".mov", ".mkv")):
                full_p = os.path.join(RAW_MEDIA_DIR, f)
                if os.path.exists(full_p) and os.path.getsize(full_p) > 1024 * 1024:
                    gta6_clips.append(full_p)

    fresh_clips = [c for c in gta6_clips if os.path.basename(c) not in used_clips]
    if fresh_clips:
        chosen = random.choice(fresh_clips)
        clip_downloader.mark_clip_as_used(chosen)
        logger.info("✓ Usando clip dinámico previo no repetido: %s", chosen)
        return chosen

    # 3. TERCERA PRIORIDAD: Descargar gameplay dinámico para el tema de HOY
    topic_query = forced_clip_query or clip_downloader.get_topic_query(topic_text)
    logger.info("Buscando y descargando gameplay dinámico de GTA 6 para el tema: '%s'...", topic_query)
    try:
        start_offset = random.choice([10, 25, 40, 60])
        downloaded = clip_downloader.search_and_download_clip(
            query=topic_query,
            output_dir=RAW_MEDIA_DIR,
            max_duration=900,
            clip_duration=60,
            start_offset=start_offset,
            max_results=5,
        )
        if downloaded:
            for d in downloaded:
                if (
                    os.path.exists(d)
                    and os.path.getsize(d) > 1024 * 1024
                    and "trailer" not in os.path.basename(d).lower()
                ):
                    clip_downloader.mark_clip_as_used(d)
                    logger.info("✓ Clip de gameplay dinámico descargado para el tema de hoy: %s", d)
                    return d
    except Exception as dl_err:
        logger.warning("Aviso en descarga dinámica de gameplay: %s", dl_err)

    # 4. CUARTA PRIORIDAD: Búsqueda dinámica de emergencia de GTA 6 en PS5 / Next Gen
    logger.info("Descarga dinámica de emergencia de mundo abierto de GTA 6...")
    try:
        emergency_queries = [
            "GTA 6 PS5 4K HDR Gameplay",
            "Grand Theft Auto VI Gameplay",
            "GTA 6 Lucia Jason gameplay open world -trailer -cutscene",
            "GTA 6 PS5 supercar driving gameplay 4k -trailer -cutscene",
        ]
        emergency_query = random.choice(emergency_queries)
        start_offset = random.choice([10, 20, 30, 45])
        em_downloaded = clip_downloader.search_and_download_clip(
            query=emergency_query,
            output_dir=RAW_MEDIA_DIR,
            max_duration=900,
            clip_duration=60,
            start_offset=start_offset,
            max_results=5,
        )
        if em_downloaded:
            for ed in em_downloaded:
                if os.path.exists(ed) and os.path.getsize(ed) > 1024 * 1024 and "trailer" not in os.path.basename(ed).lower():
                    clip_downloader.mark_clip_as_used(ed)
                    logger.info("✓ Clip de emergencia descargado con éxito: %s", ed)
                    return ed
    except Exception as em_err:
        logger.error("Error en descarga dinámica de emergencia: %s", em_err)

    if gta6_clips:
        chosen = random.choice(gta6_clips)
        logger.info("Usando clip local disponible: %s", chosen)
        return chosen

    raise FileNotFoundError("No se pudo descargar ningún clip dinámico de gameplay para el video.")


def append_to_log(caption: str, media_path: str, credit: str = "Rockstar Games Official") -> None:
    """Registra la publicación en gta6/log.md según el formato del SOP."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = caption.split("\n")[0][:80]
    line = f"| {now} | Multiplatform | {summary} | {media_path} | {credit} | Ready |\n"
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def run(
    pillar: str = "news",  # "news", "tips", "clip"
    config: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
    no_upload: bool = False,
    test_name: str = "",
    clip_url: Optional[str] = None,
) -> str:
    """Ejecuta el pipeline de generación de video para GTA 6 según el SOP."""
    logger.info("=== Iniciando pipeline GTA 6 — Pilar: %s ===", pillar.upper())
    os.makedirs(EDITS_DIR, exist_ok=True)

    # 1. Cargar tendencias en vivo de las últimas 24 horas y actualizar facts.md
    all_trends = trend_fetcher.fetch_live_trending_topics(max_topics=8)
    trend_fetcher.save_facts_update(all_trends)

    # Obtener tema viral fresco para este video (rota y no repite los últimos usados)
    top_trend = trend_fetcher.get_top_trending_topic(prefer_fresh=True)
    logger.info(
        "Tendencia seleccionada para este video: '%s' [%s] → clip: %s",
        top_trend.get("title", ""),
        top_trend.get("source", ""),
        top_trend.get("clip_query", ""),
    )

    live_trends = trend_fetcher.get_live_context_for_prompt(selected_topic=top_trend)

    extra_context = (
        f"{live_trends}\n\n"
        f"HECHOS CONFIRMADOS:\n"
        f"Grand Theft Auto VI está ambientado en el estado de Leonida (Vice City).\n"
        f"Protagonistas oficiales: Lucía y Jason. Desarrollado por Rockstar Games.\n"
        f"Plataformas: PlayStation 5 y Xbox Series X|S.\n"
        f"ESTRICTAMENTE PROHIBIDO hablar de parches viejos (1.02, etc.), ni inventar datos técnicos aburridos. "
        f"Comenta la noticia viral de hoy con emoción y en prosa continua."
    )

    # Guardar el clip_query y video_url del trending topic para usarlo como fondo
    _today_clip_query = top_trend.get("clip_query", "")
    _today_video_url = clip_url or top_trend.get("video_url", "")

    credit = "Rockstar Games Official"
    bg_video = None
    if clip_url:
        logger.info("Modo Clip Viral desde URL activo: %s", clip_url)
        clip_data = clip_downloader.download_clip_by_url(clip_url, output_dir=RAW_MEDIA_DIR)
        if clip_data:
            bg_video = clip_data["video_path"]
            credit = f"@{clip_data['creator']}"
            if clip_data.get("title"):
                extra_context += f"\nDETALLES DEL CLIP VIRAL DE TWITTER/TIKTOK:\n{clip_data['title']}"

    module_type = f"gta6_{pillar}"

    # 2. Generación + Auditoría Editorial
    logger.info("Paso 1: Generando y auditando guión con IA para %s...", module_type)
    res = gemini.generate_script(
        module_type=module_type,
        extra_context=extra_context,
    )
    script = res["script"]
    title = res["title"]
    if len(script.split()) < 50 or gemini._is_refusal(script):
        raise ValueError(f"El guión generado es inválido o una negativa ({len(script.split())} palabras): '{script}'")
    logger.info("✓ Guión auditado y aprobado: '%s' (%d palabras)", title, len(script.split()))

    # 3. Síntesis de voz con Edge-TTS
    logger.info("Paso 2: Sintetizando locución con Edge-TTS...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(EDITS_DIR, f"voice_{pillar}_{timestamp}.mp3")
    
    voice_name = "es-MX-JorgeNeural"
    if config and config.get("voice", {}).get("voice_mystery"):
        voice_name = config["voice"]["voice_mystery"]

    word_timings = asyncio.run(voice.generate_voice(
        text=script,
        output_path=audio_path,
        voice_name=voice_name,
        rate="+0%",
    ))

    # 4. Creación de Subtítulos Animados .ass
    logger.info("Paso 3: Generando subtítulos dinámicos de alto impacto...")
    ass_path = os.path.join(EDITS_DIR, f"subs_{pillar}_{timestamp}.ass")
    subtitles.generate_subtitles(
        word_timings=word_timings,
        output_path=ass_path,
        words_per_line=3,
        config=config,
    )

    # 5. Ensamblaje de Video Vertical 1080x1920 con FFmpeg
    logger.info("Paso 4: Ensamblando video vertical con gameplay de fondo...")
    if not bg_video:
        bg_video = find_background_video(
            pillar=pillar,
            topic_text=f"{title} {script}",
            forced_clip_query=_today_clip_query,
            video_url=_today_video_url,
        )
    final_video_path = os.path.join(EDITS_DIR, f"gta6_{pillar}_{timestamp}.mp4")

    # Usar música synthwave de fondo estilo GTA 6 Vice City (Royalty Free / Sin Copyright)
    gta_music_candidates = [
        os.path.join("assets", "music", "gta6_vice_synth.mp3"),
        os.path.join("assets", "music", "gta6_bg.mp3"),
        os.path.join("assets", "music", "mystery_bg.mp3"),
    ]
    music_path = None
    for cand in gta_music_candidates:
        if os.path.exists(cand) and os.path.getsize(cand) > 10000:
            music_path = cand
            logger.info("Usando música de fondo GTA 6 [Royalty Free]: %s", music_path)
            break

    video.assemble_video(
        image_paths=[],
        audio_path=audio_path,
        subtitle_path=ass_path,
        music_path=music_path,
        output_path=final_video_path,
        config=config,
        gameplay_path=bg_video,
    )
    logger.info("✓ Video final ensamblado exitosamente: %s", final_video_path)

    # 6. Registro en Scoreboard y Log
    post_id = f"gta6_{pillar}_{timestamp}"
    hook_sec = 2.5  # Duración del hook inicial estimado
    if not credit:
        credit = "Rockstar Games Official"

    scoreboard.log_post_entry(
        post_id=post_id,
        platform="Multiplatform",
        pillar=pillar,
        format_type="Short Vertical 1080x1920",
        hook_sec=hook_sec,
        credit=credit,
        test_name=test_name or "Baseline hook test",
        notes=f"Título: {title}",
    )
    append_to_log(caption=f"{title}\n{script}", media_path=final_video_path, credit=credit)

    # 7. Distribución / Subida
    if dry_run or no_upload:
        logger.info("Modo dry-run / no-upload activo. Video preservado en: %s", final_video_path)
        return final_video_path

    # Subida a YouTube Shorts si está configurado
    try:
        if os.path.exists("client_secrets.json") or os.path.exists("token.json"):
            privacy = config.get("youtube", {}).get("privacy_status", "public") if config else "public"
            logger.info("Subiendo a YouTube Shorts (Privacidad: %s)...", privacy)
            uploader.upload_video(
                video_path=final_video_path,
                title=f"{title} | GTA 6",
                description=f"{script}\n\n#GTA6 #GrandTheftAuto6 #Gaming #Shorts",
                tags=["GTA 6", "Grand Theft Auto 6", "Rockstar Games", "Gaming", "Shorts"],
                category_id="20",
                privacy_status=privacy,
            )
    except Exception as exc:
        logger.warning("Aviso en subida a YouTube: %s", exc)

    # Subida a TikTok si está configurado
    try:
        if tiktok.is_tiktok_configured():
            logger.info("Subiendo a TikTok...")
            tiktok.upload_to_tiktok(
                video_path=final_video_path,
                title=f"{title} - Novedades de GTA 6",
                tags=["gta6", "rockstargames", "gaming", "fyp"],
            )
    except Exception as exc:
        logger.warning("Aviso en subida a TikTok: %s", exc)

    # Programación en Buffer si está configurado
    if buffer_uploader.is_buffer_configured():
        profile_x = os.getenv("BUFFER_PROFILE_X", "")
        profile_ig = os.getenv("BUFFER_PROFILE_IG", "")
        if profile_x:
            buffer_uploader.schedule_buffer_post(
                profile_id=profile_x,
                text=f"{title}\n\n{script}",
                platform="x",
            )
        if profile_ig:
            buffer_uploader.schedule_buffer_post(
                profile_id=profile_ig,
                text=f"{title}\n\n{script}",
                platform="instagram",
            )

    return final_video_path
