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
import random
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
    """Retorna una historia viral de respaldo aleatoria, emocionante y adictiva.
    
    Cero temas aburridos (economía, contabilidad, hojas de cálculo). Pura tensión humana,
    venganzas inteligentes, secretos familiares y giros épicos.
    """
    viral_stories = [
        {
            "title": "Mi cuñado vendió el reloj de mi abuelo y se lo cobré en plena cena de Navidad",
            "text": (
                "Título: La venganza más satisfactoria contra mi cuñado ladrón.\n"
                "Historia: Mi cuñado aprovechó que me mudé para robar el reloj de oro que me dejó mi abuelo y lo empeñó. "
                "Cuando lo confronté, se rió en mi cara diciendo que no tenía pruebas. En lugar de pelear, fui a la tienda "
                "de empeño, compré el reloj con la factura original y esperé a la cena de Navidad con toda la familia reunida. "
                "Frente a sus padres y su esposa, le entregué como regalo la copia de la denuncia policial con su firma y video de las cámaras. "
                "Tuvo que salir corriendo mientras su propia familia le exigía explicaciones."
            ),
        },
        {
            "title": "Mi vecino construyó una cerca en mi terreno y terminó perdiendo su piscina",
            "text": (
                "Título: El vecino arrogante que quiso robarme 4 metros de patio.\n"
                "Historia: Mi vecino construyó una ampliación de su piscina invadiendo cuatro metros exactos de mi propiedad. "
                "Cuando le pedí amablemente que revisara el plano, me gritó que llamara a mis abogados porque él tenía más dinero. "
                "Hice el peritaje oficial con un topógrafo y el juez dictaminó que cualquier estructura construida en mi terreno "
                "pasaba a ser legalmente mía. Contraté albañiles y levanté un muro de concreto de tres metros que dividió su piscina por la mitad. "
                "Ahora la mitad de su agua está de mi lado y él no puede ni pisarla."
            ),
        },
        {
            "title": "Mi compañero de piso me robaba la comida hasta que usé Carolina Reaper",
            "text": (
                "Título: Lección inolvidable al ladrón de comida de mi refrigerador.\n"
                "Historia: Llevaba seis meses cocinando tuppers para toda la semana y mi compañero de piso se los comía todos sin admitirlo jamás. "
                "Siempre decía que debí habérmelos comido dormido. Cansado de la burla, preparé una lasaña deliciosa pero bañada en extracto puro "
                "de Carolina Reaper, el ají más picante del planeta. A las tres de la mañana me despertaron gritos desesperados en la cocina: "
                "estaba arrodillado frente al fregadero bebiendo leche directo del cartón con lágrimas y mocos en la cara. Nunca más volvió a tocar ni una uva ajena."
            ),
        },
        {
            "title": "Le regalé pruebas de ADN a mi familia y destapé una mentira de 30 años",
            "text": (
                "Título: El regalo de Navidad que destruyó la mentira de mi familia.\n"
                "Historia: Para Navidad compré kits de genealogía y ADN para mis padres y mis dos hermanos, pensando que sería una actividad divertida. "
                "Un mes después llegaron los resultados por correo. Mientras los míos y los de mi hermana coincidían al noventa y nueve por ciento, "
                "mi hermano mayor no compartía ni un solo gen paterno con mi papá. La mesa quedó en un silencio sepulcral mientras mi madre se ponía "
                "blanca como el papel. Lo que era una cena festiva terminó revelando una doble vida que mi madre había ocultado durante tres décadas enteras."
            ),
        },
        {
            "title": "Un estafador llamó para engañar a mi abuela y le tendí una trampa en vivo",
            "text": (
                "Título: El estafador que fue a buscar su propio arresto.\n"
                "Historia: Un tipo llamó al teléfono fijo de mi abuela diciendo que yo estaba detenido en un choque y necesitaba cinco mil dólares en efectivo. "
                "Por suerte yo estaba sentado al lado de ella. Le hice señas para que le siguiera la corriente con voz asustada y pactamos la entrega "
                "en la puerta de la casa en treinta minutos. Llamé de inmediato a la comisaría local y dos oficiales encubiertos esperaron dentro de mi sala. "
                "Cuando el sujeto llegó en su moto con una sonrisa triunfal y tocó el timbre, los policías salieron y lo redujeron en el suelo en dos segundos."
            ),
        },
        {
            "title": "La novia de mi mejor amigo exigió que pagáramos su fiesta y descubrí su secreto",
            "text": (
                "Título: La infidelidad descubierta por culpa de la avaricia.\n"
                "Historia: La prometida de mi mejor amigo nos exigió a todos los padrinos mil dólares a cada uno para pagar su despedida de soltera en un hotel de lujo. "
                "Cuando me negué, me amenazó con sacarme de la boda y prohibirle a mi amigo volverme a hablar. Sospechando de su actitud, revisé la reserva del hotel "
                "porque un amigo trabajaba en la recepción: la habitación no era para sus amigas, estaba reservada para ella y su ex novio. "
                "Le envié el comprobante con los nombres de huéspedes a mi amigo dos horas antes del ensayo de la boda. La boda se canceló de inmediato."
            ),
        },
    ]
    return random.choice(viral_stories)


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
        voice_cfg = cfg.get("voice", {})
        voice_name = voice_cfg.get("voice_reddit", "es-MX-JorgeNeural")
        voice_rate = voice_cfg.get("rate", "-4%")
        audio_path = os.path.join(work_dir, "voice.mp3")

        word_timings = asyncio.run(
            voice.generate_voice(
                text=script_text,
                output_path=audio_path,
                voice_name=voice_name,
                rate=voice_rate,
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

        # Paso 7 y 8: Subida a YouTube y TikTok
        if dry_run or no_upload:
            logger.info("[7/8] Modo DRY-RUN o NO-UPLOAD activo: saltando subida a YouTube y TikTok.")
        else:
            logger.info("[7/8] Subiendo Short a YouTube...")
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

            # Paso 8: Distribución a TikTok
            from src.core import tiktok as tiktok_module
            try:
                logger.info("[8/8] Subiendo video automáticamente a TikTok...")
                tiktok_tags = ["fyp", "parati", "reddit", "redditstories", "historias"]
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

        logger.info("=== PIPELINE REDDIT FINALIZADO CON ÉXITO ===")
        logger.info("Video final disponible en: %s", final_video_path)
        return final_video_path

    except Exception as exc:
        logger.error("Error crítico en el pipeline de Reddit: %s", exc, exc_info=True)
        raise RuntimeError(f"Fallo en ejecución del módulo Reddit: {exc}") from exc
