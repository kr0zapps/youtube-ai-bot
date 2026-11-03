"""Módulo de generación de guiones usando Groq (LLM principal) + Gemini (imágenes).

Groq usa llama-3.3-70b-versatile gratis con hasta 8.000 tokens de salida.
Sistema dual de IA: Generador + Auditor para guiones de máxima calidad viral.
Gemini se reserva para generar prompts de imágenes.
"""

import os
import re
import logging
from typing import Dict, List, Optional

from groq import Groq
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# PROMPTS — GENERADOR (Paso 1)
# ──────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Eres un guionista de élite de historias de terror, misterio y creepypastas virales para YouTube Shorts y TikTok. "
    "Tus historias tienen millones de reproducciones porque atrapan en los primeros 2 segundos con un gancho brutal "
    "y mantienen una tensión asfixiante hasta un giro final que deja a la gente con escalofríos. "
    "Narras en primera persona o hablándole directamente al espectador, de forma cercana y realista. "
    "PROHIBIDO USAR EMOJIS: Nunca uses ningún emoji ni emoticono bajo ninguna circunstancia. "
    "Nunca usas asteriscos, guiones, listas ni formato markdown. Solo texto corrido fluido con comas y puntos."
)

# ──────────────────────────────────────────────
# PROMPTS — AUDITOR (Paso 2: Filtro de calidad)
# ──────────────────────────────────────────────
AUDITOR_SYSTEM_PROMPT = (
    "Eres un editor jefe de contenido viral con 10 anos de experiencia en YouTube Shorts y TikTok de habla hispana. "
    "Tu especialidad es tomar guiones buenos y convertirlos en guiones EXCEPCIONALES que generan millones de vistas. "
    "Eres implacable, exigente y solo aceptas lo mejor. "
    "REGLAS ABSOLUTAS: "
    "1. CERO emojis ni emoticons en ningun lugar. "
    "2. CERO asteriscos, guiones, listas ni formato markdown. "
    "3. Solo texto corrido con comas y puntos, como habla real de persona. "
    "4. NUNCA uses la palabra 'relatos' en el titulo ni en el guion."
)

AUDITOR_USER_PROMPT = {
    "mystery": (
        "Tienes este borrador de guion de terror/misterio para YouTube Shorts:\n\n"
        "GUION BORRADOR:\n{draft_script}\n\n"
        "TITULO BORRADOR: {draft_title}\n\n"
        "Tu mision como editor jefe es auditarlo y reescribirlo para maximizar su potencial viral. Evalua y mejora:\n"
        "1. GANCHO (primeros 2 segundos): debe ser tan perturbador que sea imposible no seguir viendo. "
        "Si el gancho es debil o predecible, reescribelo con algo que genere miedo o curiosidad inmediata.\n"
        "2. TENSION SOSTENIDA: cada oracion debe escalar la tension. Agrega detalles sensoriales muy especificos "
        "(el olor a humedo, el crujido exacto, la sensacion de que algo te mira desde atras).\n"
        "3. GIRO FINAL: el final debe ser un golpe que deje al espectador con piel de gallina y ganas de comentar. "
        "Si el giro es predecible o flojo, cambialo por algo que nadie espera.\n"
        "4. FLUIDEZ: debe sonar como alguien contandote algo aterrador que le paso, no como texto escrito.\n"
        "5. LONGITUD: entre 135 y 160 palabras exactas. Cuenta las palabras y ajusta.\n"
        "6. TITULO: debe generar click inevitable. Maximo 55 caracteres. Sin emojis. Sin la palabra 'relatos'.\n\n"
        "Devuelve UNICAMENTE el guion mejorado sin encabezados ni explicaciones, y al final escribe:\n"
        "TITULO: [titulo mejorado]"
    ),
    "news": (
        "Tienes este borrador de guion de noticias para YouTube Shorts:\n\n"
        "GUION BORRADOR:\n{draft_script}\n\n"
        "TITULO BORRADOR: {draft_title}\n\n"
        "Mejoralo para maxima viralidad:\n"
        "1. El primer dato debe ser tan impactante que sea imposible no seguir viendo.\n"
        "2. Lenguaje claro, directo, como periodista de calle hablando a camara.\n"
        "3. Termina con una pregunta que invite a comentar.\n"
        "4. Entre 120 y 140 palabras. Cero emojis. Cero formato.\n"
        "5. Titulo impactante, maximo 60 caracteres, sin emojis.\n\n"
        "Devuelve UNICAMENTE el guion mejorado y al final:\n"
        "TITULO: [titulo mejorado]"
    ),
    "reddit": (
        "Tienes este borrador de historia de Reddit para YouTube Shorts:\n\n"
        "GUION BORRADOR:\n{draft_script}\n\n"
        "TITULO BORRADOR: {draft_title}\n\n"
        "Mejoralo para maxima viralidad:\n"
        "1. Voz muy coloquial, como contandoselo a un amigo con emocion real.\n"
        "2. Agrega reacciones y pensamientos internos autenticos.\n"
        "3. El momento de revelacion debe ser electrico.\n"
        "4. Entre 120 y 140 palabras. Cero emojis. Cero formato.\n"
        "5. Titulo enganoso en el buen sentido, maximo 60 caracteres, sin emojis.\n\n"
        "Devuelve UNICAMENTE el guion mejorado y al final:\n"
        "TITULO: [titulo mejorado]"
    ),
}

USER_PROMPTS = {
    "mystery": (
        "Escribe una historia de terror o misterio perturbadora para narrar en un YouTube Short viral.\n\n"
        "ESTRUCTURA OBLIGATORIA:\n"
        "1. GANCHO INMEDIATO (Segundos 0 a 3): Una advertencia escalofriante o una situación imposible directa al espectador. "
        "Ejemplo: 'Si vives solo y encuentras la puerta del armario ligeramente abierta esta noche, no la cierres...' o "
        "'Ayer mi teléfono recibió una llamada desde mi propio número mientras estaba en la cocina...'\n"
        "2. DESARROLLO DE TENSIÓN: Añade detalles muy reales y sensoriales (el frío repentino, un susurro familiar, una sombra que no coincide).\n"
        "3. GIRO FINAL PERTURBADOR: Una revelación inesperada que cambie todo y deje al espectador con la piel de gallina.\n\n"
        "REQUISITOS TÉCNICOS:\n"
        "- Longitud: entre 135 y 160 palabras exactas (para durar entre 50 y 55 segundos al hablar).\n"
        "- Tono: conversacional, realista, como si le contaras a un amigo algo aterrador que acaba de pasar.\n"
        "- Solo texto continuo en prosa, con comas y puntos. Sin signos raros ni formato.\n"
        "- CERO EMOJIS: Prohibido incluir cualquier emoji en el texto o en el título.\n\n"
        "Al final escribe:\n"
        "TITULO: [Título ultra viral y misterioso sin emojis, máximo 55 caracteres]\n\n"
        "Escribe la historia ahora:"
    ),
    "news": (
        "Escribe un resumen viral de esta noticia para YouTube Shorts:\n{noticia}\n\n"
        "REQUISITOS:\n"
        "- Entre 120 y 140 palabras\n"
        "- Empieza con un dato impactante o pregunta\n"
        "- Lenguaje simple y directo\n"
        "- Termina con una pregunta al espectador\n"
        "- Solo texto corrido, sin formato ni emojis\n"
        "- CERO EMOJIS: No uses emojis en ninguna parte\n\n"
        "TITULO: [título impactante sin emojis, máximo 60 caracteres]"
    ),
    "reddit": (
        "Adapta esta historia de Reddit para YouTube Shorts:\n{historia_reddit}\n\n"
        "REQUISITOS:\n"
        "- Entre 120 y 140 palabras\n"
        "- Narra en primera persona\n"
        "- Lenguaje muy coloquial, como hablando con amigos\n"
        "- Añade reacciones naturales\n"
        "- Solo texto corrido, sin formato ni emojis\n"
        "- CERO EMOJIS: No uses emojis en ninguna parte\n\n"
        "TITULO: [título impactante sin emojis, máximo 60 caracteres]"
    ),
}


def _get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY no configurada en .env")
    return Groq(api_key=key)


def _get_gemini_client():
    if genai is None:
        raise ImportError("google-genai no está instalado.")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY no configurada en .env")
    return genai.Client(api_key=key)


def remove_emojis(text: str) -> str:
    """Elimina completamente cualquier emoji o símbolo unicode decorativo."""
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff"
        "\U00002600-\U000027BF"
        "\U00002300-\U000023FF"
        "\U00002B50-\U00002B55"
        "\U0000200D\U0000FE0F"
        "]+",
        flags=re.UNICODE,
    )
    # Eliminar emojis y espacios dobles residuales
    cleaned = emoji_pattern.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"```[\w]*\n?", "", text)
    text = re.sub(r"^`|`$", "", text, flags=re.MULTILINE)
    text = remove_emojis(text)
    return text.strip()


def _parse_script_and_title(raw: str, default_title: str = "Historia de misterio") -> tuple[str, str]:
    """Extrae guión y título del texto crudo del LLM."""
    title = default_title
    if "TITULO:" in raw.upper():
        idx = raw.upper().index("TITULO:")
        script = _clean(raw[:idx])
        title = _clean(raw[idx:].split(":", 1)[-1].split("\n")[0])
    elif "---" in raw:
        parts = raw.split("---", 1)
        script = _clean(parts[0])
        title = _clean(parts[1].split("\n")[0])
    else:
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        if len(lines) >= 2 and len(lines[-1]) < 80:
            title = lines[-1]
            script = " ".join(lines[:-1])
        else:
            script = raw
    # Limpiar etiquetas residuales
    script = re.sub(r"^\*{0,2}(Guión|Script|Narración):?\*{0,2}\s*", "", script, flags=re.IGNORECASE)
    title = re.sub(r"^\*{0,2}(Título|Title|TITULO):?\*{0,2}\s*", "", title, flags=re.IGNORECASE)
    script = remove_emojis(_clean(script))
    title = remove_emojis(_clean(title))[:60]
    return script, title


def _audit_and_improve_script(
    draft_script: str,
    draft_title: str,
    module_type: str,
    client: Groq,
) -> tuple[str, str]:
    """Paso 2: Auditor de IA (openai/gpt-oss-120b) que evalúa y mejora el guión para máxima viralidad."""
    if module_type not in AUDITOR_USER_PROMPT:
        logger.warning("No hay prompt auditor para módulo '%s', saltando auditoría.", module_type)
        return draft_script, draft_title

    auditor_prompt = AUDITOR_USER_PROMPT[module_type].format(
        draft_script=draft_script,
        draft_title=draft_title,
    )

    logger.info("[DUAL-AI Paso 2/2] Auditando y mejorando guión con Auditor Viral...")
    raw_improved = None
    for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                    {"role": "user", "content": auditor_prompt},
                ],
                temperature=0.78,
                max_tokens=850,
            )
            content = response.choices[0].message.content
            if content and len(content.strip()) > 50:
                raw_improved = _clean(content)
                logger.info("Auditor completado con éxito usando Groq (%s)", model_name)
                break
        except Exception as exc:
            logger.warning("Auditor con modelo %s falló: %s", model_name, exc)

    if not raw_improved:
        try:
            gemini_c = _get_gemini_client()
            r = gemini_c.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{AUDITOR_SYSTEM_PROMPT}\n\n{auditor_prompt}",
            )
            if r.text and len(r.text.strip()) > 50:
                raw_improved = _clean(r.text)
                logger.info("Auditor completado con éxito usando Google Gemini (gemini-2.5-flash)")
        except Exception as exc_gem:
            logger.warning("Auditor con Gemini también falló: %s", exc_gem)

    if not raw_improved:
        logger.warning("Todos los modelos de auditoría fallaron. Usando borrador original.")
        return draft_script, draft_title

    improved_script, improved_title = _parse_script_and_title(raw_improved, draft_title)

    # Validar que el resultado mejorado sea sustancialmente válido
    word_count = len(improved_script.split())
    if word_count < 80:
        logger.warning("Auditor devolvió texto muy corto (%d palabras), usando borrador original.", word_count)
        return draft_script, draft_title

    logger.info(
        "Guión auditado y mejorado: %d palabras | Título: %s",
        word_count, improved_title,
    )
    return improved_script, improved_title


def generate_script(
    module_type: str,
    extra_context: Optional[str] = None,
    **kwargs,
) -> Dict[str, str]:
    """Genera guión y título usando sistema DUAL de IA:
    - Paso 1: Generador Creativo (Qwen 3.8 27B) — crea la narrativa y el suspenso.
    - Paso 2: Auditor Viral (GPT-OSS 120B) — afina el gancho, escala la tensión y pule el título.
    """
    if module_type not in USER_PROMPTS:
        raise ValueError(f"Módulo desconocido: {module_type}")

    client = _get_groq_client()

    user_prompt = USER_PROMPTS[module_type]
    if module_type == "news":
        user_prompt = user_prompt.format(noticia=extra_context or "")
    elif module_type == "reddit":
        user_prompt = user_prompt.format(historia_reddit=extra_context or "")

    # ── PASO 1: Generador — crea el borrador ──────────────────────────────────
    logger.info("[DUAL-AI Paso 1/2] Generando borrador creativo con Qwen-27B — módulo: %s", module_type)
    raw = None
    for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.92,
                max_tokens=600,
            )
            raw = _clean(response.choices[0].message.content)
            logger.info("Borrador generado con éxito usando %s", model_name)
            break
        except Exception as exc:
            logger.warning("Generador con modelo %s falló: %s", model_name, exc)

    if not raw:
        # Fallback a Gemini si Groq está caído
        logger.warning("Falló Groq para borrador, usando Gemini como fallback...")
        try:
            gemini_c = _get_gemini_client()
            r = gemini_c.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
            )
            raw = _clean(r.text)
        except Exception as exc2:
            logger.error("Error en generación con Gemini: %s", exc2)
            raise RuntimeError(f"Fallo en generación de guión: {exc2}") from exc2

    draft_script, draft_title = _parse_script_and_title(raw)
    logger.info("[Paso 1/2] Borrador: %d palabras | Título: %s", len(draft_script.split()), draft_title)

    # ── PASO 2: Auditor — audita y mejora el borrador ─────────────────────────
    final_script, final_title = _audit_and_improve_script(
        draft_script, draft_title, module_type, client
    )

    logger.info(
        "[DUAL-AI FINAL] Guión listo: %d palabras | Título: %s",
        len(final_script.split()), final_title,
    )
    return {"script": final_script, "title": final_title}


def generate_image_prompts(
    script: str,
    module_type: str,
    num_images: int = 6,
) -> List[str]:
    """Genera descripciones visuales en inglés para las imágenes usando Groq (sin cuota) o Gemini."""
    style_guide = {
        "mystery": "dark, eerie, cinematic horror lighting, photorealistic, 9:16 vertical",
        "news": "documentary photojournalism, dramatic lighting, 9:16 vertical",
        "reddit": "cinematic, emotional, relatable scene, 9:16 vertical",
    }.get(module_type, "cinematic, 9:16 vertical")

    prompt = (
        f"Based on this Spanish script (do NOT translate it, just use it as context):\n"
        f"\"\"\"{script[:500]}\"\"\"\n\n"
        f"Write exactly {num_images} DIFFERENT image descriptions in English for an AI image generator.\n"
        f"Each description must depict a DIFFERENT scene or moment from the story.\n"
        f"Style for all: {style_guide}\n"
        f"Format: one description per line, starting with number (1. 2. 3. etc.)\n"
        f"Keep each description under 80 words. No repeated scenes. No text or subtitles in images."
    )

    # Intentar primero con Groq (sin límite de cuota diaria)
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": "You are a visual art director. Generate varied, distinct image descriptions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=600,
        )
        raw = response.choices[0].message.content or ""
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        prompts = []
        for line in lines:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            # Filtrar líneas muy cortas o que sean encabezados
            if cleaned and len(cleaned) > 20 and not cleaned.startswith("Here") and not cleaned.startswith("Based"):
                prompts.append(f"{cleaned}, {style_guide}")
        if len(prompts) >= num_images:
            logger.info("Prompts de imagen generados con Groq: %d prompts", len(prompts))
            return prompts[:num_images]
        logger.debug("Groq devolvió %d prompts (necesito %d), completando...", len(prompts), num_images)
    except Exception as exc:
        logger.warning("Groq para prompts de imagen falló: %s. Intentando Gemini...", exc)

    # Fallback: Gemini
    try:
        client = _get_gemini_client()
        r = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8, max_output_tokens=600),
        )
        lines = [l.strip() for l in r.text.split("\n") if l.strip()]
        prompts = []
        for line in lines:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            if cleaned and len(cleaned) > 20:
                prompts.append(f"{cleaned}, {style_guide}")
        if len(prompts) >= num_images:
            logger.info("Prompts de imagen generados con Gemini: %d", len(prompts))
            return prompts[:num_images]
    except Exception as exc:
        logger.warning("Gemini para imágenes también falló: %s. Usando fallbacks.", exc)

    # Fallbacks hardcodeados por módulo
    defaults = {
        "mystery": [
            f"dark misty abandoned hallway with creepy shadows and dim light, {style_guide}",
            f"mysterious shadowy silhouette standing in thick fog at night, {style_guide}",
            f"old dusty attic room with strange glowing objects and cobwebs, {style_guide}",
            f"creepy forest path at midnight illuminated by pale moonlight, {style_guide}",
            f"dramatic close-up of an ancient wooden door slowly opening in darkness, {style_guide}",
            f"unsettling foggy graveyard under heavy storm clouds at dusk, {style_guide}",
        ],
        "news": [
            f"dramatic breaking news concept with global satellite view, {style_guide}",
            f"futuristic high-tech laboratory with scientists working, {style_guide}",
            f"macro shot of modern technology circuit board glowing, {style_guide}",
            f"global map with glowing digital connection lines, {style_guide}",
            f"city skyline at dusk with dramatic orange lighting, {style_guide}",
            f"journalist holding microphone in front of government building, {style_guide}",
        ],
        "reddit": [
            f"shocked young person sitting in cozy living room, mouth open, {style_guide}",
            f"dramatic coffee shop scene, person reading message on phone, {style_guide}",
            f"person walking alone on rainy city street at night, {style_guide}",
            f"awkward tense family dinner with people avoiding eye contact, {style_guide}",
            f"person staring at laptop screen in complete disbelief, {style_guide}",
            f"emotional resolution scene, person at window watching sunset, {style_guide}",
        ],
    }
    return defaults.get(module_type, defaults["mystery"])[:num_images]
