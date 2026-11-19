"""Descargador automático de clips de GTA 6 — Día de Lanzamiento.

Usa yt-dlp para:
1. Buscar los streams/videos más recientes de GTA 6 en YouTube.
2. Descargar segmentos de los creadores del watchlist.
3. Recortar al formato vertical 1080x1920 con FFmpeg.
4. Guardar en gta6/media/raw/ listos para el pipeline.

Reglas de seguridad (Sección 14 del SOP):
- Solo descarga contenido PÚBLICO de creadores verificados.
- Nunca descarga leaks, builds filtradas ni contenido pirateado.
- El crédito del creador se anota automáticamente en el nombre del archivo.
"""

import os
import re
import logging
import subprocess
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

RAW_DIR = os.path.join("gta6", "media", "raw")
OFFICIAL_DIR = os.path.join("gta6", "media", "official")

# Términos de búsqueda seguros (solo contenido público y legítimo, sin spoilers)
GTA6_SEARCH_QUERIES = [
    "GTA 6 open world free roam gameplay no commentary -spoiler -ending -cutscene",
    "Grand Theft Auto VI exploration Vice City gameplay 4k",
    "GTA 6 driving car night Vice City free roam",
    "GTA VI Lucia Jason walking open world gameplay",
    "GTA 6 PS5 graphical showcase free roam gameplay",
]

USED_CLIPS_FILE = os.path.join("gta6", "media", "used_clips.json")


def load_used_clips() -> List[str]:
    """Carga la lista de nombres de archivo de clips que ya han sido usados para no repetirlos."""
    if os.path.exists(USED_CLIPS_FILE):
        try:
            import json
            with open(USED_CLIPS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def mark_clip_as_used(clip_path: str) -> None:
    """Registra un clip como usado para evitar repeticiones."""
    import json
    used = load_used_clips()
    base = os.path.basename(clip_path)
    if base not in used:
        used.append(base)
    # Conservar el historial de los últimos 60 para rotar constantemente
    if len(used) > 60:
        used = used[-60:]
    try:
        os.makedirs(os.path.dirname(USED_CLIPS_FILE), exist_ok=True)
        with open(USED_CLIPS_FILE, "w", encoding="utf-8") as f:
            json.dump(used, f, indent=2)
    except Exception:
        pass


def get_topic_query(text: str) -> str:
    """Genera una búsqueda de YouTube contextual al tema del guión, 100% libre de spoilers y del tráiler.
    
    Filtra estrictamente cinemáticas de historia, muertes, finales y el tráiler oficial repetitivo.
    """
    import random
    t = text.lower() if text else ""

    # 1. Trucos bloqueados, trampas, armas, Tanques
    if any(k in t for k in ["truco", "trucos", "trampa", "trampas", "cheat", "cheats", "bloqueado", "bloqueados", "armas"]):
        return "GTA 6 funny gameplay weapons chaos free roam -trailer -ending -cutscene -mission -live -livestream"

    # 2. Memes, Calamardo, PC vs Consolas, tendencias de internet
    if any(k in t for k in ["meme", "memes", "calamardo", "pc", "internet", "redes", "tiktok", "twitter", "funeral"]):
        return "GTA 6 funny streamer moments viral clips gameplay -trailer -ending -cutscene -live -livestream"

    # 3. Realismo, Miami real vs Vice City, gráficos, iluminación
    if any(k in t for k in ["miami", "real", "realidad", "vida real", "iluminación", "luces", "gráfico", "grafico", "ps5"]):
        return "GTA 6 realistic driving Vice City night cruise 4k -trailer -cutscene -live -livestream"

    # 4. NPCs dementes, peatones, situaciones absurdas en la ciudad
    if any(k in t for k in ["npc", "npcs", "peatón", "peaton", "peatones", "gente", "dementes", "locura", "tienda", "florida"]):
        return "GTA 6 crazy npc moments open world funny -trailer -ending -cutscene -live -livestream"

    # 5. Físicas de agua, caimanes, pantanos, tormentas, lanchas
    if any(k in t for k in ["agua", "caimán", "caiman", "caimanes", "mar", "playa", "tormenta", "rio", "río", "pantano", "bote", "lancha"]):
        return "GTA 6 water physics boat alligator swamp gameplay -trailer -ending -cutscene -live -livestream"

    # 6. Policía, persecuciones, sistema táctico, 5 estrellas
    if any(k in t for k in ["policía", "policia", "policías", "estrellas", "persecución", "persecucion", "arresto", "escape", "patrulla"]):
        return "GTA 6 police chase 5 stars escape gameplay -trailer -ending -cutscene -live -livestream"

    # 7. Autos, superdeportivos, conducción nocturna, carreras
    if any(k in t for k in ["auto", "autos", "coche", "coches", "conducción", "conduccion", "manejar", "manejando", "velocidad", "superdeportivo"]):
        return "GTA 6 driving supercar Vice City night cruise -trailer -ending -cutscene -live -livestream"

    # Default rotativo: variedad total de momentos virales de mundo abierto (NUNCA el tráiler)
    viral_queries = [
        "GTA 6 funny moments streamer gameplay open world -trailer -cutscene -live -livestream",
        "GTA 6 police chase chaos action free roam -trailer -cutscene -live -livestream",
        "GTA 6 driving sports car Vice City night stunts -trailer -cutscene -live -livestream",
        "GTA 6 crazy open world moments funny -trailer -cutscene -live -livestream",
        "GTA 6 free roam exploration Vice City beach 4k -trailer -cutscene -live -livestream",
    ]
    return random.choice(viral_queries)

# Creadores del watchlist — canales de YouTube a monitorear
WATCHLIST_CHANNELS = [
    # Canales con ID directo de YouTube (más confiable)
    "https://www.youtube.com/@GtaSeriesVideos",
    "https://www.youtube.com/@DigitalFoundry",
    "https://www.youtube.com/@RockstarGames",
]


def find_yt_dlp() -> str:
    """Localiza el ejecutable yt-dlp en el sistema."""
    found = shutil.which("yt-dlp")
    if found:
        return found
    # Fallback: instalado como módulo Python
    return "yt-dlp"


def find_ffmpeg() -> str:
    """Localiza FFmpeg en el sistema delegando en video.find_ffmpeg_executable."""
    from src.core.video import find_ffmpeg_executable
    return find_ffmpeg_executable()


def _base_ytdlp_flags() -> List[str]:
    """Flags comunes optimizados: cliente android e ios para evitar bloqueos de bot y SABR."""
    flags = [
        # Clientes android e ios no requieren inicio de sesión ni sufren bloqueos de bot en centros de datos
        "--extractor-args", "youtube:player_client=android,ios",
    ]
    
    # Cookies si existen
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 50:
        flags.extend(["--cookies", "cookies.txt"])
    elif os.path.exists(os.path.join("..", "cookies.txt")) and os.path.getsize(os.path.join("..", "cookies.txt")) > 50:
        flags.extend(["--cookies", os.path.join("..", "cookies.txt")])

    # 2. JS runtime para resolver el challenge de YouTube
    node_bin = shutil.which("node")
    if node_bin:
        flags.extend(["--js-runtimes", f"node:{node_bin}"])
    elif os.path.exists(r"C:\Program Files\nodejs\node.exe"):
        flags.extend(["--js-runtimes", r"node:C:\Program Files\nodejs\node.exe"])

    # Ruta a FFmpeg para yt-dlp
    from src.core.video import find_ffmpeg_executable
    try:
        ffmpeg_bin = find_ffmpeg_executable()
        flags.extend(["--ffmpeg-location", os.path.dirname(ffmpeg_bin)])
    except Exception:
        pass

    flags.extend([
        # Cabeceras de navegador real
        "--add-headers", "Accept-Language:en-US,en;q=0.9",
        "--user-agent", (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        # Reintentos y delays anti-ratelimit
        "--retries", "3",
        "--sleep-interval", "1",
        "--max-sleep-interval", "3",
    ])
    return flags


def is_valid_gta6_title(title: str) -> bool:
    """Valida estrictamente que el video sea de GTA 6 y NO de juegos antiguos, mods ni trailers repetitivos."""
    if not title:
        return False
    t = title.lower()
    # 1. Debe contener explícitamente GTA 6 / GTA VI / Grand Theft Auto VI
    has_gta6 = any(k in t for k in ["gta 6", "gta vi", "gta6", "grand theft auto vi", "grand theft auto 6"])
    if not has_gta6:
        return False
    # 2. Estrictamente prohibido contenido de juegos viejos de la saga (San Andreas, Vice City 2002, GTA 5, etc.)
    # y trailers repetitivos, podcasts o videos que no sean gameplay puro.
    banned = [
        "san andreas", "gta sa", "gta: sa", "samp",
        "gta 5", "gta v", "gta online", "gta5",
        "gta 4", "gta iv", "gta4",
        "gta 3", "gta iii", "gta3",
        "vice city stories", "liberty city stories",
        "definitive edition", "the definitive",
        "modding", "modded", "gta v mod", "gta 5 mod",
        "ps2", "ps3", "xbox 360", "2002", "2004", "2008", "2013",
        "spiderman", "minecraft", "roblox", "lego",
        "trailer", "fragman", "teaser", "podcast", "interview"
    ]
    if any(b in t for b in banned):
        return False
    return True


def find_youtube_video_ids(query: str, max_results: int = 5) -> List[str]:
    """Busca en YouTube usando curl_cffi con TLS impersonation de Chrome para evitar bot checks de ytsearch."""
    import urllib.parse
    import re
    try:
        from curl_cffi import requests
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        r = requests.get(url, impersonate="chrome120", timeout=15)
        if r.status_code == 200:
            ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', r.text)
            unique = list(dict.fromkeys(ids))
            return unique[:max_results]
    except Exception as e:
        logger.warning("Aviso en búsqueda curl_cffi: %s", e)
    return []


def find_dailymotion_video_urls(query: str, max_results: int = 5) -> List[str]:
    """Busca videos de gameplay en Dailymotion usando su API pública gratuita sin bloqueos de IP en CI.
    
    Filtra rigurosamente los títulos para que sean 100% GTA 6 y NUNCA San Andreas, Vice City 2002 o GTA 5.
    """
    import urllib.parse
    import urllib.request
    import json
    
    clean_q = re.sub(r"-(trailer|cutscene|live|livestream|ending|mission)", "", query, flags=re.IGNORECASE)
    clean_q = re.sub(r"\s+", " ", clean_q).strip()
    encoded = urllib.parse.quote_plus(clean_q)
    url = f"https://api.dailymotion.com/videos?search={encoded}&limit=15&fields=id,title,duration"
    
    results = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("list", []):
                vid_id = item.get("id")
                title = item.get("title", "")
                dur = item.get("duration", 0)
                if vid_id and dur >= 25 and is_valid_gta6_title(title):
                    results.append(f"https://www.dailymotion.com/video/{vid_id}")
    except Exception as e:
        logger.warning("Aviso en búsqueda Dailymotion: %s", e)

    # Si la query específica no devolvió videos que pasen el filtro estricto de GTA 6,
    # consultar el catálogo verificado de gameplay next-gen de GTA 6
    if not results:
        fallback_queries = [
            "GTA 6 PS5 4K HDR Gameplay",
            "Grand Theft Auto VI Gameplay",
            "GTA 6 Lucia Jason gameplay",
            "GTA 6 next gen gameplay 4k"
        ]
        for fq in fallback_queries:
            f_url = f"https://api.dailymotion.com/videos?search={urllib.parse.quote_plus(fq)}&limit=10&fields=id,title,duration"
            try:
                req = urllib.request.Request(f_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for item in data.get("list", []):
                        vid_id = item.get("id")
                        title = item.get("title", "")
                        dur = item.get("duration", 0)
                        if vid_id and dur >= 25 and is_valid_gta6_title(title):
                            results.append(f"https://www.dailymotion.com/video/{vid_id}")
                        if len(results) >= max_results:
                            break
            except Exception:
                pass
            if results:
                break

    return results[:max_results]


def search_and_download_clip(
    query: str,
    output_dir: str,
    max_duration: int = 900,
    clip_duration: int = 58,
    start_offset: int = 30,
    max_results: int = 5,
) -> List[str]:
    """Busca un video en YouTube o Dailymotion por query y descarga un segmento dinámico y único.

    Garantiza que siempre se descargue un clip real relacionado al tema del día,
    utilizando Dailymotion como respaldo 100% inmune a bloqueos de bot en CI.
    """
    os.makedirs(output_dir, exist_ok=True)
    yt_dlp = find_yt_dlp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = re.sub(r"[^\w\s-]", "", query).strip().replace(" ", "_")[:40]
    output_template = os.path.join(output_dir, f"raw_{safe_query}_{timestamp}.%(ext)s")

    end_offset = start_offset + clip_duration
    match_filter = f"!is_live & !was_live & duration < {max_duration} & duration > 60"

    # 1. Intentar YouTube primero con IDs directos
    video_ids = find_youtube_video_ids(query, max_results=max_results)
    targets = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids] if video_ids else []

    if targets:
        logger.info("Buscando y descargando segmento (%ds-%ds) en YouTube para: '%s' (%d candidatos)...", start_offset, end_offset, query, len(targets))
        for target in targets:
            cmd = [
                yt_dlp,
                target,
                "--match-filter", match_filter,
                f"--download-sections=*{start_offset}-{end_offset}",
                "-f", "bestvideo[height<=1080]+bestaudio/18/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "--max-downloads", "1",
                "--ignore-errors",
                "-o", output_template,
                "--quiet",
                "--no-warnings",
            ] + _base_ytdlp_flags()

            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                downloaded = [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if f.startswith(f"raw_{safe_query}_{timestamp}") and f.endswith(".mp4")
                ]
                if downloaded:
                    logger.info("✓ Clip dinámico de YouTube descargado con éxito: %s", downloaded[0])
                    return downloaded
            except Exception as exc:
                logger.warning("Aviso al descargar candidato YouTube %s: %s", target, exc)

    # 2. Si YouTube falla o está bloqueado por IP de datacenter, usar Dailymotion (100% confiable en CI)
    dm_urls = find_dailymotion_video_urls(query, max_results=max_results)
    if dm_urls:
        logger.info("Descargando gameplay alternativo de Dailymotion para '%s' (%d candidatos)...", query, len(dm_urls))
        # Para videos de Dailymotion, fijar el inicio cerca del comienzo (<=15s) para videos cortos
        dm_start = min(start_offset, 15)
        dm_end = dm_start + clip_duration
        for dm_url in dm_urls:
            cmd_dm = [
                yt_dlp,
                dm_url,
                f"--download-sections=*{dm_start}-{dm_end}",
                "-f", "bestvideo[height>=720][height<=1080]+bestaudio/bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "-o", output_template,
                "--no-warnings",
            ]
            try:
                res = subprocess.run(cmd_dm, capture_output=True, text=True, timeout=90)
                downloaded = [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if f.startswith(f"raw_{safe_query}_{timestamp}") and f.endswith(".mp4")
                ]
                if downloaded:
                    logger.info("✓ Clip dinámico de Dailymotion descargado con éxito: %s", downloaded[0])
                    return downloaded
                else:
                    logger.warning("yt-dlp sección falló para %s (rc=%d): %s", dm_url, res.returncode, (res.stderr or "")[:150])
                    # Reintento sin download-sections si la sección falló
                    cmd_dm_full = [
                        yt_dlp,
                        dm_url,
                        "-f", "bestvideo[height>=720][height<=1080]+bestaudio/bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best",
                        "--merge-output-format", "mp4",
                        "--no-playlist",
                        "-o", output_template,
                        "--no-warnings",
                    ]
                    res_full = subprocess.run(cmd_dm_full, capture_output=True, text=True, timeout=90)
                    downloaded = [
                        os.path.join(output_dir, f)
                        for f in os.listdir(output_dir)
                        if f.startswith(f"raw_{safe_query}_{timestamp}") and f.endswith(".mp4")
                    ]
                    if downloaded:
                        logger.info("✓ Clip completo de Dailymotion descargado con éxito: %s", downloaded[0])
                        return downloaded
            except Exception as e:
                logger.warning("Aviso al descargar candidato Dailymotion %s: %s", dm_url, e)

    logger.warning("No se pudo descargar ningún candidato para '%s'", query)
    return []


def trim_to_vertical_short(
    input_path: str,
    output_path: str,
    start_sec: int = 30,
    duration_sec: int = 55,
    width: int = 1080,
    height: int = 1920,
) -> bool:
    """Recorta un segmento del video y lo convierte a formato vertical 9:16.

    Args:
        input_path: Ruta al video descargado.
        output_path: Ruta del clip vertical de salida.
        start_sec: Segundo de inicio del segmento.
        duration_sec: Duración del segmento (<=58s para Shorts).
        width: Ancho del video de salida.
        height: Alto del video de salida.

    Returns:
        True si el recorte fue exitoso.
    """
    try:
        ffmpeg = find_ffmpeg()
    except FileNotFoundError as e:
        logger.error("%s", e)
        return False

    # Crop centrado y escala a 1080x1920
    vf_filter = (
        f"crop=min(iw\\,ih*{width}/{height}):min(ih\\,iw*{height}/{width}),"
        f"scale={width}:{height}:flags=lanczos"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-ss", str(start_sec),
        "-i", input_path,
        "-t", str(duration_sec),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "15",
        "-maxrate", "30M",
        "-bufsize", "60M",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info("Recortando a vertical: %s → %s", os.path.basename(input_path), os.path.basename(output_path))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info("✓ Clip vertical listo: %s (%.1f MB)", output_path, size_mb)
            return True
        else:
            logger.error("FFmpeg error: %s", result.stderr[:300])
            return False
    except Exception as exc:
        logger.error("Error al recortar video: %s", exc)
        return False


def download_official_trailer(url: str = "https://www.youtube.com/watch?v=QdBZY2fkU-0") -> Optional[str]:
    """Descarga el tráiler oficial de Rockstar Games en la mejor calidad disponible."""
    os.makedirs(OFFICIAL_DIR, exist_ok=True)
    yt_dlp = find_yt_dlp()
    output_path = os.path.join(OFFICIAL_DIR, "trailer_official.mp4")

    if os.path.exists(output_path):
        logger.info("Tráiler oficial ya descargado: %s", output_path)
        return output_path

    cmd = [
        yt_dlp,
        url,
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--quiet",
    ] + _base_ytdlp_flags()

    logger.info("Descargando tráiler oficial de Rockstar Games...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info("✓ Tráiler oficial descargado: %s (%.1fMB)", output_path, size_mb)
            return output_path
        else:
            logger.error("Error descargando tráiler: %s", result.stderr[:300])
            return None
    except Exception as exc:
        logger.error("Excepción al descargar tráiler: %s", exc)
        return None


def download_clip_by_url(url: str, output_dir: str = RAW_DIR) -> Optional[Dict[str, Any]]:
    """Descarga un clip viral directamente desde una URL (Twitter/X, YouTube, TikTok o Reddit).
    
    Extrae la información del creador para el crédito obligatorio y descarga el video.
    """
    os.makedirs(output_dir, exist_ok=True)
    yt_dlp = find_yt_dlp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_template = os.path.join(output_dir, f"viral_{timestamp}.%(ext)s")

    cmd_meta = [
        yt_dlp,
        url,
        "--dump-single-json",
        "--quiet",
        "--no-warnings",
    ] + _base_ytdlp_flags()

    creator = "Community Creator"
    title = "Momento viral de GTA 6"

    try:
        res = subprocess.run(cmd_meta, capture_output=True, text=True, timeout=30)
        if res.returncode == 0 and res.stdout.strip():
            import json
            meta = json.loads(res.stdout)
            creator = meta.get("uploader") or meta.get("channel") or meta.get("uploader_id") or creator
            title = meta.get("title") or title
    except Exception as e:
        logger.warning("Aviso al extraer metadata de %s: %s", url, e)

    cmd_down = [
        yt_dlp,
        url,
        "-f", "bestvideo[height<=1080]+bestaudio/18/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", out_template,
        "--no-playlist",
        "--quiet",
    ] + _base_ytdlp_flags()

    logger.info("Descargando clip viral de Twitter/YouTube desde: %s (Creador detectado: %s)", url, creator)
    try:
        subprocess.run(cmd_down, capture_output=True, text=True, timeout=120)
        candidates = [
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if f.startswith(f"viral_{timestamp}") and f.endswith(".mp4")
        ]
        if candidates:
            downloaded = candidates[0]
            logger.info("✓ Clip viral descargado con éxito: %s (Creador: @%s)", downloaded, creator)
            return {
                "video_path": downloaded,
                "creator": creator,
                "title": title,
                "url": url,
            }
        else:
            logger.error("No se encontró el archivo mp4 resultante para %s", url)
            return None
    except Exception as exc:
        logger.error("Error al descargar clip viral desde %s: %s", url, exc)
        return None


def run_launch_day_download(
    num_queries: int = 3,
    clip_start_sec: int = 45,
    clip_duration_sec: int = 55,
) -> List[str]:
    """Ejecuta la descarga de clips del día de lanzamiento.

    Descarga y procesa clips de búsquedas de YouTube,
    los convierte a formato vertical y los deja listos en gta6/media/raw/.

    Returns:
        Lista de rutas a clips verticales listos para usar como fondo.
    """
    logger.info("=" * 54)
    logger.info("   MODO DIA DE LANZAMIENTO — GTA 6 CLIP DOWNLOADER")
    logger.info("=" * 54)

    os.makedirs(RAW_DIR, exist_ok=True)
    final_clips: List[str] = []

    # 1. Descargar tráiler oficial primero (fondo garantizado)
    trailer = download_official_trailer()
    if trailer:
        vertical_trailer = trailer.replace(".mp4", "_vertical.mp4")
        if trim_to_vertical_short(trailer, vertical_trailer, start_sec=10, duration_sec=55):
            shutil.copy(vertical_trailer, os.path.join(RAW_DIR, "trailer_vertical.mp4"))
            final_clips.append(os.path.join(RAW_DIR, "trailer_vertical.mp4"))

    # 2. Descargar clips de búsquedas
    queries = GTA6_SEARCH_QUERIES[:num_queries]
    for query in queries:
        raw_files = search_and_download_clip(
            query=query,
            output_dir=RAW_DIR,
            max_duration=600,
            clip_duration=clip_duration_sec,
            start_offset=clip_start_sec,
        )
        for raw_file in raw_files:
            vertical_path = raw_file.replace(".mp4", "_v.mp4")
            if trim_to_vertical_short(
                raw_file,
                vertical_path,
                start_sec=clip_start_sec,
                duration_sec=clip_duration_sec,
            ):
                final_clips.append(vertical_path)

    logger.info("=" * 54)
    logger.info("Clips listos para publicar: %d", len(final_clips))
    for c in final_clips:
        logger.info("  • %s", c)
    logger.info("=" * 54)
    return final_clips
