"""MÃ³dulo de ensamblaje de video con FFmpeg.

Ensambla imÃ¡genes verticales (1080x1920) con transiciones fade entre cada imagen,
mezcla la voz con mÃºsica de fondo calibrada al 15% y quema subtÃ­tulos animados (.ass).
"""

import os
import re
import shutil
import logging
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def find_ffmpeg_executable(config: Optional[Dict[str, Any]] = None) -> str:
    """Encuentra la ruta del binario ffmpeg en el sistema."""
    if config and config.get("video", {}).get("ffmpeg_path"):
        custom_path = config["video"]["ffmpeg_path"]
        if os.path.isfile(custom_path):
            return custom_path

    env_ffmpeg = os.environ.get("FFMPEG_PATH")
    if env_ffmpeg and os.path.isfile(env_ffmpeg):
        return env_ffmpeg

    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    user_profile = os.environ.get("USERPROFILE", r"C:\Users\krosa")
    candidate_paths = [
        os.path.join(user_profile, "Videos", "ffmpeg.exe"),
        os.path.join(user_profile, r"AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]

    for candidate in candidate_paths:
        if os.path.isfile(candidate):
            logger.info("FFmpeg detectado en ruta del sistema: %s", candidate)
            return candidate

    raise FileNotFoundError(
        "No se encontrÃ³ el ejecutable 'ffmpeg'. AsegÃºrate de tener FFmpeg instalado."
    )


def get_audio_duration(audio_path: str, ffmpeg_bin: str) -> float:
    """Determina la duraciÃ³n exacta de un archivo de audio en segundos usando FFmpeg."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

    cmd = [ffmpeg_bin, "-i", audio_path]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
        if match:
            hours, minutes, seconds = match.groups()
            total_sec = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
            logger.info("DuraciÃ³n de audio calculada: %.2f segundos (%s)", total_sec, audio_path)
            return total_sec
    except Exception as exc:
        logger.warning("Fallo al obtener duraciÃ³n con FFmpeg: %s", exc)

    size_bytes = os.path.getsize(audio_path)
    estimated = max(10.0, (size_bytes * 8) / (48 * 1000))
    return estimated


def _format_ffmpeg_path(path: str) -> str:
    """Formatea una ruta para ser compatible con filtros complejos de FFmpeg en Windows."""
    clean = os.path.abspath(path).replace("\\", "/")
    if len(clean) > 1 and clean[1] == ":":
        clean = clean[0] + r"\:" + clean[2:]
    return clean


def extract_thumbnail(
    video_path: str,
    output_thumb_path: str,
    timestamp_sec: float = 2.5,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Extrae un fotograma vertical en alta resolución (1080x1920) para usar de miniatura.

    Captura exactamente el momento donde la tarjeta de Reddit está completamente visible y centrada.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video no encontrado para miniatura: {video_path}")

    ffmpeg_bin = find_ffmpeg_executable(config)
    os.makedirs(os.path.dirname(os.path.abspath(output_thumb_path)), exist_ok=True)

    cmd = [
        ffmpeg_bin, "-y",
        "-ss", f"{timestamp_sec:.2f}",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_thumb_path,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    logger.info("✓ Miniatura extraída con tarjeta de Reddit: %s", output_thumb_path)
    return output_thumb_path


def assemble_video(
    image_paths: List[str],
    audio_path: str,
    subtitle_path: Optional[str],
    music_path: Optional[str],
    output_path: str,
    config: Optional[Dict[str, Any]] = None,
    gameplay_path: Optional[str] = None,
    reddit_card_path: Optional[str] = None,
) -> str:
    """Ensambla el video final vertical (1080x1920).

    Modos:
    - gameplay_path proporcionado → usa el clip de gameplay como fondo (mejor resultado)
    - image_paths → usa imágenes con fade entre cada una
    """
    if not gameplay_path and not image_paths:
        raise ValueError("Se requiere gameplay_path o image_paths.")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"No existe el archivo de audio: {audio_path}")

    cfg_video = config.get("video", {}) if config else {}
    width = cfg_video.get("width", 1080)
    height = cfg_video.get("height", 1920)
    fps = cfg_video.get("fps", 30)

    ffmpeg_bin = find_ffmpeg_executable(config)
    audio_duration = get_audio_duration(audio_path, ffmpeg_bin)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # ── MODO GAMEPLAY 2x2 (Full Dopamina): 4 gameplays simultáneos en grid ────────
    from src.core import gameplay as gp_mod
    dopamine_clips = gp_mod.get_dopamine_2x2_clips()
    if len(dopamine_clips) >= 4:
        logger.info("Modo 2x2 FULL DOPAMINA activo con 4 gameplays: %s", [os.path.basename(c) for c in dopamine_clips[:4]])
        return _assemble_with_dopamine_2x2(
            gameplay_paths=dopamine_clips[:4],
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            music_path=music_path,
            output_path=output_path,
            audio_duration=audio_duration,
            ffmpeg_bin=ffmpeg_bin,
            width=width, height=height, fps=fps,
            reddit_card_path=reddit_card_path,
        )

    # ── MODO GAMEPLAY SIMPLE: usar un solo clip de video como fondo ──────────
    if gameplay_path and os.path.exists(gameplay_path):
        logger.info("Modo GAMEPLAY simple: usando %s como fondo", os.path.basename(gameplay_path))
        return _assemble_with_gameplay(
            gameplay_path=gameplay_path,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            music_path=music_path,
            output_path=output_path,
            audio_duration=audio_duration,
            ffmpeg_bin=ffmpeg_bin,
            width=width, height=height, fps=fps,
            reddit_card_path=reddit_card_path,
        )

    # â”€â”€ MODO IMÃGENES: clips con fade â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    num_images = len(image_paths)
    duration_per_image = max(3.0, audio_duration / num_images)

    logger.info(
        "Iniciando ensamble: %d imÃ¡genes, duraciÃ³n total: %.2fs, %.2fs/imagen",
        num_images, audio_duration, duration_per_image,
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # â”€â”€ Paso 1: Generar un clip .mp4 por imagen con fade in/out â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    clip_paths = []
    fade_duration = min(0.5, duration_per_image * 0.08)
    fade_out_start = max(0.1, duration_per_image - fade_duration)

    # Movimientos Ken Burns: (zoom_inicio, zoom_fin, x_pan_expr, y_pan_expr)
    kb_moves = [
        # zoom in lento desde centro
        (1.0, 1.15, "0", "0"),
        # zoom out desde esquina superior derecha
        (1.15, 1.0, f"-{int(width*0.1)}", f"-{int(height*0.05)}"),
        # zoom in desde abajo izquierda
        (1.0, 1.12, f"{int(width*0.05)}", f"{int(height*0.05)}"),
        # zoom out suave
        (1.12, 1.0, "0", f"-{int(height*0.05)}"),
        # zoom in desde arriba derecha
        (1.0, 1.15, f"-{int(width*0.08)}", "0"),
        # zoom out desde abajo
        (1.15, 1.0, f"{int(width*0.05)}", f"{int(height*0.08)}"),
    ]

    for idx, img_path in enumerate(image_paths):
        clip_out = output_path.replace(".mp4", f"_clip{idx:02d}.mp4")
        clip_paths.append(clip_out)

        z_start, z_end, pan_x, pan_y = kb_moves[idx % len(kb_moves)]
        # Escalar la imagen mÃ¡s grande para dar espacio al paneo
        scale_w = int(width * 1.2)
        scale_h = int(height * 1.2)
        # Paneo suave usando zoompan simplificado: solo zoom, sin paneo complejo
        frames = int(duration_per_image * fps)

        # Construir filtro de video para este clip
        vf = (
            f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
            f"crop={scale_w}:{scale_h},"
            f"scale={width}:{height},"
            f"fade=t=in:st=0:d={fade_duration:.3f},"
            f"fade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}"
        )

        cmd_clip = [
            ffmpeg_bin, "-y",
            "-loop", "1", "-t", f"{duration_per_image:.3f}", "-i", img_path,
            "-vf", vf,
            "-r", str(fps),
            "-t", f"{duration_per_image:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            clip_out,
        ]

        logger.info("Generando clip %d/%d: %s", idx + 1, num_images, os.path.basename(img_path))
        proc = subprocess.run(
            cmd_clip,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            logger.error("Error generando clip %d: %s", idx, proc.stderr[-300:])
            # Clip simple sin efectos como fallback
            cmd_simple = [
                ffmpeg_bin, "-y",
                "-loop", "1", "-t", f"{duration_per_image:.3f}", "-i", img_path,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                "-r", str(fps), "-c:v", "libx264", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-an", clip_out,
            ]
            subprocess.run(cmd_simple, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, encoding="utf-8", errors="replace")

    # â”€â”€ Paso 2: Crear lista de concat para FFmpeg (rutas absolutas) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    concat_list_path = output_path.replace(".mp4", "_concat.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for cp in clip_paths:
            abs_cp = os.path.abspath(cp).replace("\\", "/")
            f.write(f"file '{abs_cp}'\n")

    # â”€â”€ Paso 3: Unir clips con concat demuxer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    silent_video = output_path.replace(".mp4", "_silent.mp4")
    cmd_concat = [
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "copy",
        silent_video,
    ]
    logger.info("Concatenando %d clips...", num_images)
    proc_concat = subprocess.run(
        cmd_concat,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    if proc_concat.returncode != 0:
        logger.error("Error en concat: %s", proc_concat.stderr[-300:])
        raise RuntimeError("Fallo al concatenar clips de video.")

    # â”€â”€ Paso 4: Mezclar audio + subtÃ­tulos sobre el video â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    has_music = bool(music_path and os.path.exists(music_path))

    input_args = ["-i", silent_video, "-i", audio_path]
    if has_music:
        input_args.extend(["-stream_loop", "-1", "-i", music_path])

    filter_parts = []

    # SubtÃ­tulos
    if subtitle_path and os.path.exists(subtitle_path):
        escaped_sub = _format_ffmpeg_path(subtitle_path)
        fonts_dir = _format_ffmpeg_path(os.path.join("assets", "fonts"))
        filter_parts.append(
            f"[0:v]subtitles=filename='{escaped_sub}':fontsdir='{fonts_dir}'[vout]"
        )
    else:
        filter_parts.append("[0:v]null[vout]")

    # Audio
    if has_music:
        filter_parts.append(
            "[1:a]volume=1.0[avoice];"
            "[2:a]volume=0.15[amusic];"
            "[avoice][amusic]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:
        filter_parts.append("[1:a]volume=1.0[aout]")

    cmd_final = [
        ffmpeg_bin, "-y",
        *input_args,
        "-filter_complex", ";\n".join(filter_parts),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{audio_duration:.2f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    logger.info("Ensamblando video final con audio y subtÃ­tulos...")
    try:
        proc_final = subprocess.run(
            cmd_final,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Error en ensamble final: %s", exc.stderr[-400:])

        # Fallback sin subtÃ­tulos
        if subtitle_path and "subtitles" in exc.stderr:
            logger.warning("Reintentando sin subtÃ­tulos...")
            cmd_nosub = [
                ffmpeg_bin, "-y",
                "-i", silent_video, "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-t", f"{audio_duration:.2f}",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                output_path,
            ]
            subprocess.run(cmd_nosub, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, encoding="utf-8", errors="replace", check=True)
        else:
            raise RuntimeError(f"Fallo en ensamble de video: {exc.stderr[:400]}") from exc

    # â”€â”€ Limpieza de archivos temporales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    for cp in clip_paths:
        try:
            os.remove(cp)
        except OSError:
            pass
    for tmp in [concat_list_path, silent_video]:
        try:
            os.remove(tmp)
        except OSError:
            pass

    logger.info("Video ensamblado con Ã©xito: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path


def _assemble_with_gameplay(
    gameplay_path: str,
    audio_path: str,
    subtitle_path: Optional[str],
    music_path: Optional[str],
    output_path: str,
    audio_duration: float,
    ffmpeg_bin: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    reddit_card_path: Optional[str] = None,
) -> str:
    """Ensambla el video usando un clip de gameplay como fondo con punto de inicio aleatorio."""
    import random
    has_music = bool(music_path and os.path.exists(music_path))
    has_card = bool(reddit_card_path and os.path.exists(reddit_card_path))
    whoosh_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio", "whoosh.mp3"))
    has_whoosh = bool(has_card and os.path.exists(whoosh_path))

    # Obtener duración del gameplay para elegir un inicio aleatorio
    gameplay_duration = get_audio_duration(gameplay_path, ffmpeg_bin)
    seek_args = []
    if gameplay_duration > audio_duration + 10:
        max_start = gameplay_duration - audio_duration - 5
        start_sec = random.uniform(0, max_start)
        logger.info("Gameplay (%.1fs total): inicio aleatorio en t=%.1fs", gameplay_duration, start_sec)
        seek_args = ["-ss", f"{start_sec:.2f}"]

    input_args = [*seek_args, "-stream_loop", "-1", "-i", gameplay_path, "-i", audio_path]
    cur_idx = 2

    music_idx = None
    if has_music:
        input_args.extend(["-stream_loop", "-1", "-i", music_path])
        music_idx = cur_idx
        cur_idx += 1

    whoosh_idx = None
    if has_whoosh:
        input_args.extend(["-i", whoosh_path])
        whoosh_idx = cur_idx
        cur_idx += 1

    card_idx = None
    if has_card:
        input_args.extend(["-loop", "1", "-i", reddit_card_path])
        card_idx = cur_idx
        cur_idx += 1

    filter_parts = []

    # Video: escalar gameplay a 1080x1920 con máxima nitidez, colores vivos y filtro unsharp
    vf_base = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"eq=brightness=0.01:saturation=1.12,"
        f"unsharp=5:5:0.6:5:5:0.0[vbg]"
    )
    filter_parts.append(vf_base)
    last_v = "vbg"

    # Hook visual de Reddit: animación suave de entrada y salida con fade (duración extendida ~7.5s)
    if has_card:
        filter_parts.append(
            f"[{card_idx}:v]fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st=7.0:d=0.5:alpha=1[cardfaded];"
            f"[{last_v}][cardfaded]overlay=x=(W-w)/2:y='if(lt(t,0.25), 360-150*(1-t/0.25)*(1-t/0.25), if(gt(t,7.0), 360-600*(t-7.0)*(t-7.0), 360))':enable='between(t,0,7.55)':eof_action=repeat[vcard]"
        )
        last_v = "vcard"

    if subtitle_path and os.path.exists(subtitle_path):
        escaped_sub = _format_ffmpeg_path(subtitle_path)
        fonts_dir = _format_ffmpeg_path(os.path.join("assets", "fonts"))
        filter_parts.append(
            f"[{last_v}]subtitles=filename='{escaped_sub}':fontsdir='{fonts_dir}'[vout]"
        )
    else:
        filter_parts.append(f"[{last_v}]null[vout]")

    # Audio: voz destacada + música de fondo + efecto whoosh de entrada
    audio_inputs = ["[1:a]volume=1.4[avoice]"]
    mix_sources = ["[avoice]"]

    if has_music:
        audio_inputs.append(f"[{music_idx}:a]volume=0.20[amusic]")
        mix_sources.append("[amusic]")

    if has_whoosh:
        audio_inputs.append(f"[{whoosh_idx}:a]volume=0.85[awhoosh]")
        mix_sources.append("[awhoosh]")

    if len(mix_sources) > 1:
        filter_parts.extend(audio_inputs)
        filter_parts.append(
            f"{''.join(mix_sources)}amix=inputs={len(mix_sources)}:duration=first:dropout_transition=0:normalize=0[aout]"
        )
    else:
        filter_parts.append("[1:a]volume=1.0[aout]")

    cmd = [
        ffmpeg_bin, "-y",
        *input_args,
        "-filter_complex", ";\n".join(filter_parts),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{audio_duration:.2f}",
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-maxrate", "12M", "-bufsize", "24M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k",
        output_path,
    ]

    logger.info("Ensamblando video con gameplay + audio + subtÃ­tulos...")
    try:
        subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Error en modo gameplay: %s", exc.stderr[-400:])
        # Fallback sin subtÃ­tulos
        if subtitle_path and "subtitles" in exc.stderr:
            logger.warning("Reintentando sin subtÃ­tulos...")
            cmd_nosub = [
                ffmpeg_bin, "-y",
                "-stream_loop", "-1", "-i", gameplay_path, "-i", audio_path,
                "-vf", f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width}:{height}",
                "-map", "0:v", "-map", "1:a",
                "-t", f"{audio_duration:.2f}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                output_path,
            ]
            subprocess.run(cmd_nosub, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, encoding="utf-8", errors="replace")
        else:
            raise RuntimeError(f"Fallo en modo gameplay: {exc.stderr[:300]}") from exc

    logger.info("Video gameplay ensamblado: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path


def _assemble_with_dopamine_2x2(
    gameplay_paths: List[str],
    audio_path: str,
    subtitle_path: Optional[str],
    music_path: Optional[str],
    output_path: str,
    audio_duration: float,
    ffmpeg_bin: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    reddit_card_path: Optional[str] = None,
) -> str:
    """Ensambla el video en formato 2x2 'Full Dopamina' con 4 gameplays simultáneos:
    - Superior Izquierda (540x960): Subway Surfers
    - Superior Derecha (540x960): Minecraft Parkour
    - Inferior Izquierda (540x960): GTA 5 Mega Ramp
    - Inferior Derecha (540x960): CS Surf / Parkour
    """
    import random
    has_music = bool(music_path and os.path.exists(music_path))
    has_card = bool(reddit_card_path and os.path.exists(reddit_card_path))
    whoosh_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio", "whoosh.mp3"))
    has_whoosh = bool(has_card and os.path.exists(whoosh_path))

    half_w = width // 2   # 540
    half_h = height // 2  # 960

    input_args = []
    # 4 gameplays inputs (0, 1, 2, 3)
    for gp in gameplay_paths[:4]:
        gp_dur = get_audio_duration(gp, ffmpeg_bin)
        seek_args = []
        if gp_dur > audio_duration + 10:
            max_start = gp_dur - audio_duration - 5
            start_sec = random.uniform(0, max_start)
            seek_args = ["-ss", f"{start_sec:.2f}"]
        input_args.extend([*seek_args, "-stream_loop", "-1", "-i", gp])

    # Audio voz (input 4)
    input_args.extend(["-i", audio_path])
    cur_idx = 5

    music_idx = None
    if has_music:
        input_args.extend(["-stream_loop", "-1", "-i", music_path])
        music_idx = cur_idx
        cur_idx += 1

    whoosh_idx = None
    if has_whoosh:
        input_args.extend(["-i", whoosh_path])
        whoosh_idx = cur_idx
        cur_idx += 1

    card_idx = None
    if has_card:
        input_args.extend(["-loop", "1", "-i", reddit_card_path])
        card_idx = cur_idx
        cur_idx += 1

    filter_parts = []
    # Escalar y recortar cada uno de los 4 cuadrantes a 540x960
    for i in range(4):
        filter_parts.append(
            f"[{i}:v]scale={half_w}:{half_h}:force_original_aspect_ratio=increase,"
            f"crop={half_w}:{half_h},fps={fps}[v{i}]"
        )

    # Combinar en grid 2x2 usando xstack
    filter_parts.append(
        f"[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0,"
        f"eq=brightness=0.01:saturation=1.12[vbg]"
    )
    last_v = "vbg"

    # Tarjeta de Reddit animada centrada con fade in y slide out (duración extendida ~7.5s)
    if has_card:
        filter_parts.append(
            f"[{card_idx}:v]fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st=7.0:d=0.5:alpha=1[cardfaded];"
            f"[{last_v}][cardfaded]overlay=x=(W-w)/2:y='if(lt(t,0.25), 360-150*(1-t/0.25)*(1-t/0.25), if(gt(t,7.0), 360-600*(t-7.0)*(t-7.0), 360))':enable='between(t,0,7.55)':eof_action=repeat[vcard]"
        )
        last_v = "vcard"

    if subtitle_path and os.path.exists(subtitle_path):
        escaped_sub = _format_ffmpeg_path(subtitle_path)
        fonts_dir = _format_ffmpeg_path(os.path.join("assets", "fonts"))
        filter_parts.append(
            f"[{last_v}]subtitles=filename='{escaped_sub}':fontsdir='{fonts_dir}'[vout]"
        )
    else:
        filter_parts.append(f"[{last_v}]null[vout]")

    # Audio mixing
    audio_inputs = ["[4:a]volume=1.4[avoice]"]
    mix_sources = ["[avoice]"]

    if has_music:
        audio_inputs.append(f"[{music_idx}:a]volume=0.20[amusic]")
        mix_sources.append("[amusic]")

    if has_whoosh:
        audio_inputs.append(f"[{whoosh_idx}:a]volume=0.85[awhoosh]")
        mix_sources.append("[awhoosh]")

    if len(mix_sources) > 1:
        filter_parts.extend(audio_inputs)
        filter_parts.append(
            f"{''.join(mix_sources)}amix=inputs={len(mix_sources)}:duration=first:dropout_transition=0:normalize=0[aout]"
        )
    else:
        filter_parts.append("[4:a]volume=1.0[aout]")

    cmd = [
        ffmpeg_bin, "-y",
        *input_args,
        "-filter_complex", ";\n".join(filter_parts),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{audio_duration:.2f}",
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k",
        output_path,
    ]

    logger.info("Ensamblando video 2x2 FULL DOPAMINA con 4 gameplays simultáneos...")
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", check=True)
    logger.info("✓ Video 2x2 Full Dopamina ensamblado: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path

