"""Módulo de generación de subtítulos animados en formato ASS (Advanced SubStation Alpha).

Genera subtítulos dinámicos de alto impacto visual estilo Shorts/TikTok/Reels,
con texto grande centrado en la parte inferior, borde oscuro grueso
y resaltado palabra por palabra (karaoke visual).
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def format_ass_time(seconds: float) -> str:
    """Convierte segundos a formato de tiempo ASS (H:MM:SS.cc)."""
    if seconds < 0:
        seconds = 0.0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int(round((seconds - int(seconds)) * 100))

    if centiseconds >= 100:
        centiseconds = 99

    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _get_font_name(preferred_font: str = "Bebas Neue") -> str:
    """Verifica si la fuente existe en assets/fonts o retorna una alternativa universal."""
    # Revisar carpeta local de fuentes del proyecto
    local_font_paths = [
        os.path.join("assets", "fonts", "BebasNeue-Regular.ttf"),
        os.path.join("assets", "fonts", "BebasNeue.ttf"),
    ]
    for path in local_font_paths:
        if os.path.exists(path):
            return "Bebas Neue"

    # Revisar fuentes estándar de Windows
    windir = os.environ.get("WINDIR", r"C:\Windows")
    windows_fonts = os.path.join(windir, "Fonts")
    for fname in ["BebasNeue-Regular.ttf", "BebasNeue.ttf"]:
        if os.path.exists(os.path.join(windows_fonts, fname)):
            return "Bebas Neue"

    # Alternativas universales y llamativas
    for candidate in ["Impact", "Arial Black", "Montserrat", "Arial"]:
        return candidate

    return "Arial"


def generate_subtitles(
    word_timings: List[Dict[str, Any]],
    output_path: str,
    words_per_line: int = 3,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Genera un archivo de subtítulos .ass con animación de palabra activa.

    Args:
        word_timings: Lista de diccionarios con 'word', 'start' y 'end'.
        output_path: Ruta del archivo .ass de destino.
        words_per_line: Número de palabras mostradas simultáneamente por tarjeta.
        config: Diccionario opcional de configuración de subtítulos.

    Returns:
        Ruta del archivo .ass generado.
    """
    if not word_timings:
        logger.warning("Lista de tiempos vacía. Generando archivo de subtítulos vacío.")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nTitle: Empty\n[Events]\n")
        return output_path

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Parámetros visuales desde config o valores por defecto
    sub_config = config.get("subtitles", {}) if config else {}
    font_name = sub_config.get("font", "Bebas Neue")
    font_size = sub_config.get("font_size", 76)
    words_per_subtitle = sub_config.get("words_per_subtitle", words_per_line)

    resolved_font = _get_font_name(font_name)
    logger.info("Generando subtítulos ASS con fuente '%s' en: %s", resolved_font, output_path)

    # Encabezado del formato ASS para video vertical 1080x1920
    # Alignment 2 = Abajo Centrado. MarginV 260 asegura que no lo tapen los botones de Shorts.
    # Colores en formato &HAABBGGRR:
    # Blanco: &H00FFFFFF
    # Amarillo Neón de resalte: &H0000E5FF
    # Borde negro: &H00000000
    ass_header = f"""[Script Info]
Title: YouTube AI Bot Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{resolved_font},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5.5,1.5,2,40,40,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines: List[str] = []

    # Agrupar palabras en paquetes de 'words_per_subtitle'
    groups = []
    for i in range(0, len(word_timings), words_per_subtitle):
        chunk = word_timings[i : i + words_per_subtitle]
        if chunk:
            groups.append(chunk)

    for group in groups:
        # Para cada grupo de palabras, generamos una micro-línea por cada palabra activa
        # resaltándola en amarillo mientras se pronuncia
        for word_idx, active_item in enumerate(group):
            start_str = format_ass_time(active_item["start"])
            end_str = format_ass_time(active_item["end"])

            # Asegurar duración mínima para evitar parpadeos
            if active_item["end"] <= active_item["start"]:
                end_str = format_ass_time(active_item["start"] + 0.15)

            # Construir texto con la palabra actual resaltada
            formatted_words = []
            for idx, item in enumerate(group):
                word_clean = item["word"].strip().upper()
                if idx == word_idx:
                    # Resaltado amarillo neón con ligero aumento de escala
                    formatted_words.append(r"{\c&H0000E5FF\fscx108\fscy108}" + word_clean + r"{\r}")
                else:
                    # Color blanco principal
                    formatted_words.append(r"{\c&H00FFFFFF}" + word_clean)

            line_text = " ".join(formatted_words)
            dialogue_lines.append(
                f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}"
            )

    full_content = ass_header + "\n".join(dialogue_lines) + "\n"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)
        logger.info("Subtítulos generados con éxito: %d líneas de diálogo creadas.", len(dialogue_lines))
    except Exception as exc:
        logger.error("Error al escribir el archivo .ass: %s", exc)
        raise RuntimeError(f"Fallo al guardar subtítulos ASS: {exc}") from exc

    return output_path
