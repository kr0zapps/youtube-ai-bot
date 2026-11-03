"""Módulo de síntesis de voz con Edge-TTS.

Convierte texto a audio MP3 con calidad neural y extrae marcas de tiempo
por cada palabra para la generación sincronizada de subtítulos.
"""

import os
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
import edge_tts
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _align_with_whisper(audio_path: str) -> Optional[List[Dict[str, Any]]]:
    """Usa Whisper Large V3 en Groq para obtener marcas de tiempo acústicas exactas palabra por palabra."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), f.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        raw_words = getattr(transcription, "words", None)
        if raw_words:
            whisper_timings = []
            for w in raw_words:
                word_str = w.get("word") if isinstance(w, dict) else getattr(w, "word", "")
                start_sec = w.get("start") if isinstance(w, dict) else getattr(w, "start", 0.0)
                end_sec = w.get("end") if isinstance(w, dict) else getattr(w, "end", 0.0)
                if word_str:
                    whisper_timings.append({
                        "word": word_str.strip(),
                        "start": round(float(start_sec), 3),
                        "end": round(float(end_sec), 3),
                    })
            if whisper_timings:
                logger.info("✓ Sincronización acústica milimétrica con Whisper Groq: %d palabras", len(whisper_timings))
                return whisper_timings
    except Exception as exc:
        logger.warning("Fallo al alinear con Whisper Groq: %s. Usando marcas de tiempo de Edge-TTS.", exc)
    return None


def _estimate_fallback_timings(text: str, total_duration: float, start_offset: float = 0.4) -> List[Dict[str, Any]]:
    """Genera marcas de tiempo estimadas si el motor no devolvió WordBoundary.
    
    Args:
        text: Texto completo del guión.
        total_duration: Duración total del audio en segundos.
        start_offset: Delay inicial en segundos antes del primer subtítulo.
    """
    words = re.findall(r"\S+", text)
    if not words:
        return []

    # Restar el delay inicial de la duración disponible
    available_duration = max(1.0, total_duration - start_offset)
    time_per_word = max(0.15, available_duration / len(words))
    timings = []
    current_time = start_offset  # Empezar con delay

    for word in words:
        start = current_time
        end = min(total_duration, current_time + time_per_word)
        timings.append({
            "word": word,
            "start": round(start, 3),
            "end": round(end, 3),
        })
        current_time = end

    return timings


async def generate_voice(
    text: str,
    output_path: str,
    voice_name: str = "es-ES-AlvaroNeural",
    rate: str = "+0%",
    volume: str = "+0%",
) -> List[Dict[str, Any]]:
    """Convierte texto en audio MP3 usando Edge-TTS y extrae los tiempos de cada palabra.

    Args:
        text: Texto a sintetizar en voz.
        output_path: Ruta del archivo MP3 de salida.
        voice_name: Nombre de la voz neuronal (ej: es-ES-AlvaroNeural).
        rate: Ajuste de velocidad (ej: '+0%', '+10%').
        volume: Ajuste de volumen (ej: '+0%').

    Returns:
        Lista de diccionarios con la estructura:
        [{"word": str, "start": float, "end": float}]

    Raises:
        RuntimeError: Si ocurre un error durante la síntesis.
    """
    if not text or not text.strip():
        raise ValueError("El texto para generar voz no puede estar vacío.")

    # Asegurar que el directorio de salida exista
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Generando voz con Edge-TTS (voz: %s) en: %s", voice_name, output_path)

    word_timings: List[Dict[str, Any]] = []

    try:
        communicate = edge_tts.Communicate(
            text=text.strip(),
            voice=voice_name,
            rate=rate,
            volume=volume,
        )

        with open(output_path, "wb") as audio_file:
            async for chunk in communicate.stream():
                chunk_type = chunk.get("type")
                if chunk_type == "audio":
                    audio_file.write(chunk.get("data", b""))
                elif chunk_type == "WordBoundary":
                    offset_ticks = chunk.get("offset", 0)
                    duration_ticks = chunk.get("duration", 0)
                    word_str = chunk.get("text", "").strip()
                    if word_str:
                        word_timings.append({
                            "word": word_str,
                            "start": round(offset_ticks / 10_000_000.0, 3),
                            "end": round((offset_ticks + duration_ticks) / 10_000_000.0, 3),
                        })
                elif chunk_type == "SentenceBoundary":
                    # SentenceBoundary contiene marcas de tiempo exactas por oración
                    offset_ticks = chunk.get("offset", 0)
                    duration_ticks = chunk.get("duration", 0)
                    sentence_text = chunk.get("text", "").strip()
                    if sentence_text:
                        s_start = offset_ticks / 10_000_000.0
                        s_end = (offset_ticks + duration_ticks) / 10_000_000.0
                        words_in_s = re.findall(r"\S+", sentence_text)
                        if words_in_s:
                            w_dur = (s_end - s_start) / len(words_in_s)
                            for i, w in enumerate(words_in_s):
                                word_timings.append({
                                    "word": w,
                                    "start": round(s_start + i * w_dur, 3),
                                    "end": round(s_start + (i + 1) * w_dur, 3),
                                })

        file_size = os.path.getsize(output_path)
        logger.info(
            "Audio generado exitosamente: %s (tamaño: %d bytes)",
            output_path,
            file_size,
        )

        # 1. Intentar alineación acústica milimétrica con Whisper Large V3 (Groq)
        whisper_timings = _align_with_whisper(output_path)
        if whisper_timings:
            return whisper_timings

        # 2. Fallback: usar marcas de SentenceBoundary de Edge-TTS
        if word_timings:
            logger.info("Usando marcas de tiempo por oración de Edge-TTS (%d palabras)", len(word_timings))
            return word_timings

        # 3. Fallback final si no hay marcas: estimar tiempos
        logger.warning("Estimando tiempos de subtítulos por duración total...")
        estimated_duration = max(3.0, (file_size * 8) / (48 * 1000))
        return _estimate_fallback_timings(text, estimated_duration, start_offset=0.1)

    except Exception as exc:
        logger.error("Error al generar voz con Edge-TTS: %s", exc, exc_info=True)
        # Limpiar archivo corrupto si existe
        if os.path.exists(output_path) and os.path.getsize(output_path) == 0:
            try:
                os.remove(output_path)
            except OSError:
                pass
        raise RuntimeError(f"Fallo en síntesis de voz: {exc}") from exc


def generate_voice_sync(
    text: str,
    output_path: str,
    voice_name: str = "es-ES-AlvaroNeural",
) -> List[Dict[str, Any]]:
    """Versión síncrona de generate_voice para comodidad en scripts bloqueantes."""
    return asyncio.run(generate_voice(text, output_path, voice_name))
