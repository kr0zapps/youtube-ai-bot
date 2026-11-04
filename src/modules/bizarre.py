"""Módulo de Cosas Bizarras, Gente Loca y Situaciones Caóticas ("Cosas Mierdas / Desastres Épicos").

Pipeline automatizado que:
1. Selecciona anécdotas virales absurdas, desastres sociales o momentos donde el karma
   aplastó a gente sinvergüenza (estilo r/trashy, r/tifu, r/InsanePeople).
2. Genera un guión con la fórmula de retención 2026: Hook en 2s, Micro-hook a los 15s,
   duración 35-45s y cierre con Infinite Loop.
3. Filtro estricto con IA Auditora (cero aburrimiento corporativo, 100% entretenimiento adictivo).
4. Sintetiza la locución con Edge-TTS (voz casual Jorge).
5. Fondo aleatorio de gameplay 1080p60 (Subway Surfers, CS:GO Surf, Minecraft, GTA).
6. Subtítulos ASS de alto contraste en zona segura de TikTok/Shorts.
7. Publica en YouTube Shorts y TikTok.
"""

import os
import yaml
import shutil
import logging
import asyncio
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from src.core import gemini, voice, subtitles, video, uploader
from src.core import gameplay as gameplay_module

load_dotenv()
logger = logging.getLogger(__name__)

VIRAL_BIZARRE_STORIES = [
    {
        "title": "Mi vecina falsa intentó robarse mi paquete y quedó grabada en 4K",
        "text": (
            "Título: La ladrona de paquetes que se creyó invisible.\n"
            "Historia: Mi vecina del cuarto piso esperó a que el repartidor dejara una caja en mi puerta para salir en pantuflas "
            "y meterla en su bolso creyendo que nadie la veía. Lo que no sabía es que mi mirilla tiene una cámara oculta con sensor "
            "y alerta en directo a mi teléfono. En lugar de gritarle, imprimí la captura de su cara sosteniendo mi paquete en tamaño "
            "póster y la pegué en el ascensor del edificio con el texto: 'Se busca vecina cleptómana'. "
            "A la media hora me dejó la caja en la puerta con una nota llorando suplicando que quitara los carteles."
        ),
    },
    {
        "title": "Un cliente soberbio me tiró el café encima y el dueño resultó ser mi tío",
        "text": (
            "Título: El karma instantáneo más dulce del mundo.\n"
            "Historia: Trabajaba de mesero en una cafetería y un sujeto con traje me tiró su taza al suelo porque la espuma no estaba perfecta. "
            "Me gritó que era un inútil y que llamara al dueño porque era íntimo amigo suyo y me iba a dejar en la calle. "
            "Fui a la oficina trasera y salió el dueño: mi tío Carlos, fundador del local. El tipo sonrió creyendo que venía a despedirme, "
            "pero mi tío lo miró de arriba abajo y le dijo: 'No tengo la menor idea de quién eres, pero acabas de agredir a mi sobrino. "
            "Tienes diez segundos para limpiar el piso o la policía te saca esposado'."
        ),
    },
    {
        "title": "La dama de honor intentó boicotear la boda de mi hermana y terminó humillada",
        "text": (
            "Título: Boicot arruinado en plena ceremonia.\n"
            "Historia: En la boda de mi hermana, una de sus supuestas mejores amigas llegó vestida de blanco brillante para robarse la atención. "
            "Cuando mi hermana la vio casi se pone a llorar, pero la abuela de la familia no tuvo piedad: se levantó con una copa de vino tinto, "
            "fingió tropezar con la alfombra y se la vació entera de arriba a abajo sobre el vestido blanco. "
            "La chica gritó como desquiciada mientras todos los invitados aplaudían creyendo que era una tradición. Tuvo que marcharse en un taxi cubierta de vino."
        ),
    },
    {
        "title": "Mi compañero de piso fingía ser sonámbulo para robarme dinero de la cartera",
        "text": (
            "Título: El sonámbulo que se curó de golpe.\n"
            "Historia: Cada semana me faltaban billetes y mi compañero de piso juraba que él caminaba dormido y no recordaba nada. "
            "Decidí poner a prueba su sonambulismo médico: puse un billete falso con tinta indeleble violeta que mancha la piel por días "
            "y una alarma silenciosa en mi billetera. A las dos de la madrugada la alarma vibró en mi reloj. Fui a su cuarto y lo encontré "
            "despierto con las dos manos completamente teñidas de morado fluorescente, intentando lavarse desesperado con alcohol. "
            "Se quedó congelado y empacó sus maletas esa misma noche sin decir una sola palabra."
        ),
    },
    {
        "title": "Un estafador de marketplace vino a mi casa y la policía lo estaba esperando",
        "text": (
            "Título: Venta de teléfono con final inesperado.\n"
            "Historia: Puse en venta mi consola usada y un comprador insistió en pagar con transferencia falsa mostrándome un comprobante trucado en Photoshop. "
            "Le dije amablemente que viniera a mi dirección para entregarle el paquete. Lo que no le advertí es que vivo justo al lado de la comisaría central "
            "y mi vecino es capitán de homicidios. Cuando llegó haciéndose el matón exigiendo la caja sin que el dinero estuviera en mi cuenta, "
            "dos patrullas le cerraron el paso por detrás. El tipo terminó llorando en la vereda mientras los oficiales le incautaban el auto por papeles adulterados."
        ),
    },
]


def _get_random_bizarre_story() -> Dict[str, str]:
    """Retorna una historia bizarra / caótica aleatoria."""
    return random.choice(VIRAL_BIZARRE_STORIES)


def _load_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    """Ejecuta el pipeline completo del módulo de Situaciones Bizarras / Gente Loca."""
    cfg = _load_config(config)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output = output_dir or os.path.join("output", "bizarre")
    work_dir = os.path.join(base_output, f"temp_{timestamp}")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(base_output, exist_ok=True)

    logger.info("=== INICIANDO PIPELINE: SITUACIONES BIZARRAS / CAOS [%s] ===", timestamp)

    try:
        # Paso 1: Selección de anécdota bizarra base
        logger.info("[1/7] Seleccionando anécdota caótica base...")
        story_data = _get_random_bizarre_story()

        # Paso 2: Generación y Doble Filtro de IA (Generador + Auditor de Retención)
        logger.info("[2/7] Generando y auditando con Doble IA para retención máxima...")
        model_name = cfg.get("gemini", {}).get("model", "gemini-2.0-flash-lite")
        temperature = cfg.get("gemini", {}).get("temperature", 0.9)
        max_tokens = cfg.get("gemini", {}).get("max_output_tokens", 800)

        script_data = gemini.generate_script(
            module_type="bizarre",
            extra_context=story_data["text"],
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        script_text = script_data["script"]
        video_title = script_data["title"]

        with open(os.path.join(work_dir, "script.txt"), "w", encoding="utf-8") as f:
            f.write(f"Historia base: {story_data['title']}\n")
            f.write(f"Título Short: {video_title}\n\nGuión:\n{script_text}\n")

        # Paso 3: Síntesis de voz con Edge-TTS
        logger.info("[3/7] Sintetizando voz con Edge-TTS...")
        voice_cfg = cfg.get("voice", {})
        voice_name = voice_cfg.get("voice_bizarre", "es-MX-JorgeNeural")
        voice_rate = voice_cfg.get("rate", "+0%")
        audio_path = os.path.join(work_dir, "voice.mp3")

        word_timings = asyncio.run(
            voice.generate_voice(
                text=script_text,
                output_path=audio_path,
                voice_name=voice_name,
                rate=voice_rate,
            )
        )

        # Paso 4: Fondo de gameplay viral (Subway Surfers, CSGO Surf, Minecraft, GTA)
        logger.info("[4/7] Seleccionando fondo de gameplay viral...")
        gameplay_clip = gameplay_module.get_random_gameplay_clip()
        if not gameplay_clip:
            raise RuntimeError("No se encontró ningún clip de gameplay en assets/gameplay/")

        logger.info("✓ Gameplay activo: %s", os.path.basename(gameplay_clip))

        # Paso 5: Subtítulos ASS en la Golden Zone
        logger.info("[5/7] Generando subtítulos karaoke dinámicos...")
        ass_path = os.path.join(work_dir, "subtitles.ass")
        subtitles.generate_subtitles(
            word_timings=word_timings,
            output_path=ass_path,
            words_per_line=3,
            config=cfg,
        )

        # Paso 5.5: Generar tarjeta visual de Reddit / Post viral (Hook de retención)
        from src.core import reddit_card
        card_path = os.path.join(work_dir, "reddit_card.png")
        try:
            reddit_card.generate_reddit_card(
                hook_text=script_text[:190],
                output_path=card_path,
                category="bizarre",
                theme=random.choice(["light", "dark"]),
            )
        except Exception as c_err:
            logger.warning("Aviso tarjeta bizarro: %s", c_err)
            card_path = None

        # Paso 6: Renderizado de video 1080x1920 60fps con FFmpeg
        logger.info("[6/7] Ensamblando video vertical...")
        final_video_path = os.path.join(base_output, f"bizarre_{timestamp}.mp4")
        video.assemble_video(
            image_paths=[],
            audio_path=audio_path,
            subtitle_path=ass_path,
            music_path=None,
            output_path=final_video_path,
            config=cfg,
            gameplay_path=gameplay_clip,
            reddit_card_path=card_path if (card_path and os.path.exists(card_path)) else None,
        )

        # Paso 6.5: Extraer miniatura oficial con la tarjeta de Reddit visible (t=2.5s)
        thumb_path = final_video_path.replace(".mp4", "_thumb.jpg")
        try:
            video.extract_thumbnail(final_video_path, thumb_path, timestamp_sec=2.5, config=cfg)
        except Exception as th_err:
            logger.warning("No se pudo extraer miniatura automática: %s", th_err)
            thumb_path = None

        # Paso 7: Publicación a YouTube y TikTok
        if dry_run or no_upload:
            logger.info("[7/8] Modo DRY-RUN o NO-UPLOAD activo: saltando subida a YouTube y TikTok.")
        else:
            logger.info("[7/8] Publicando video en YouTube Shorts y TikTok...")
            # Tags algorítmicos hiper-relevantes
            hashtags = "#shorts #historias #bizarro #chisme #karma"
            desc = f"{video_title}\n\n{hashtags}"

            # YouTube
            try:
                uploader.upload_video(
                    video_path=final_video_path,
                    title=f"{video_title} #shorts",
                    description=desc,
                    tags=["shorts", "historias", "bizarro", "chisme", "karma", "reddit"],
                    category_id="24",
                    thumbnail_path=thumb_path,
                )
            except Exception as u_err:
                logger.error("Error al subir a YouTube: %s", u_err)

            # TikTok
            try:
                from src.core import tiktok as tiktok_module
                tiktok_tags = ["fyp", "parati", "bizarro", "chisme", "karma"]
                tiktok_module.upload_to_tiktok(
                    video_path=final_video_path,
                    title=video_title,
                    tags=tiktok_tags,
                    cover_path=thumb_path,
                )
            except Exception as t_err:
                logger.error("Error al subir a TikTok: %s", t_err)

        if not dry_run:
            shutil.rmtree(work_dir, ignore_errors=True)
            logger.info("Carpeta temporal limpiada: %s", work_dir)

        logger.info("=== PIPELINE BIZARRE FINALIZADO CON ÉXITO ===")
        logger.info("Video final disponible en: %s", final_video_path)
        return final_video_path

    except Exception as exc:
        logger.error("Error crítico en el pipeline de Cosas Bizarras: %s", exc, exc_info=True)
        raise RuntimeError(f"Fallo en ejecución del módulo Bizarre: {exc}") from exc
