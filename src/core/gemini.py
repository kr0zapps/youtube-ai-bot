"""Módulo de generación de guiones usando Groq (LLM principal) + Gemini (imágenes).

Groq usa llama-3.3-70b-versatile gratis con hasta 8.000 tokens de salida.
Sistema dual de IA: Generador + Auditor para guiones de máxima calidad viral.
Gemini se reserva para generar prompts de imágenes.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any

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
SYSTEM_PROMPTS = {
    "mystery": (
        "Eres un novelista y guionista maestro del suspense psicológico y misterio oscuro para YouTube Shorts y TikTok. "
        "FÓRMULA DE RETENCIÓN 2026:\n"
        "1. GANCHO (0 a 3s): Empieza directamente en medio de una situación perturbadora o un descubrimiento aterrador. "
        "Cero saludos ni explicaciones lentas.\n"
        "2. MICRO-HOOK (a los 15s): Introduce un reenganche ('Pero lo que vi después...', 'En ese instante me di cuenta de mi error...').\n"
        "3. COHERENCIA TOTAL: Verosimilitud absoluta, causa y efecto realista (cámaras de seguridad, llamadas grabadas, vecinos, casas antiguas).\n"
        "4. BUCLE INFINITO (Infinite Loop): La frase final debe conectar con la frase inicial sin que se note el corte.\n"
        "PROHIBIDO USAR EMOJIS ni formato markdown. Solo prosa fluida continua con comas y puntos."
    ),
    "reddit": (
        "Eres un narrador maestro de historias virales de Reddit de máximo impacto emocional y morbo social (estilo r/confessions, r/tifu, r/BestofRedditorUpdates, r/pettyrevenge). "
        "FÓRMULA DE RETENCIÓN 2026:\n"
        "1. GANCHO (0 a 3s): Suelta una bomba humana de inmediato que impida deslizar el video.\n"
        "2. CERO TEMAS ABURRIDOS: Estrictamente prohibido hablar de economía, hojas de cálculo, contabilidad, contratos corporativos o burocracia de oficina. Las historias deben tratar sobre dramas humanos: infidelidades, secretos familiares, venganzas personales deliciosas contra arrogantes o vecinos insoportables.\n"
        "3. MICRO-HOOK (a los 15s): Renueva la tensión antes de que el espectador se distraiga.\n"
        "4. BUCLE INFINITO: Cierra con una frase que enlace fluidamente de vuelta al inicio.\n"
        "PROHIBIDO USAR EMOJIS ni formato markdown. Lenguaje directo y coloquial."
    ),
    "bizarre": (
        "Eres el narrador definitivo de historias insólitas, desastres sociales, situaciones caóticas y gente sinvergüenza (estilo r/trashy, r/tifu, momentos virales de 'cosas mierdas / ridículas'). "
        "FÓRMULA DE RETENCIÓN 2026:\n"
        "1. GANCHO (0 a 3s): Arranca con la estupidez o insolencia más grande que alguien haya hecho jamás.\n"
        "2. TONO IRÓNICO Y ADICTIVO: Mezcla de asombro y sátira, narrando cómo el karma aplastó a alguien que se creía intocable (un estafador torpe, una boda boicoteada, un vecino sinvergüenza humillado en público).\n"
        "3. MICRO-HOOK (a los 15s): Escalada de la vergüenza ajena o el desastre.\n"
        "4. BUCLE INFINITO: Final épico y satisfactorio que conecta con la apertura.\n"
        "PROHIBIDO USAR EMOJIS ni formato markdown. Cero temas aburridos."
    ),
    "news": (
        "Eres un periodista de divulgación científica y sucesos insólitos para YouTube Shorts y TikTok. "
        "REGLA DE ORO: RIGOR Y COHERENCIA TOTAL. Explicas misterios resueltos, descubrimientos arqueológicos "
        "o fenómenos fascinantes con causa y efecto claros. CERO TEMAS POLÍTICOS O ECONÓMICOS ABURRIDOS. "
        "PROHIBIDO USAR EMOJIS ni formato markdown."
    ),
}

# ──────────────────────────────────────────────
# PROMPTS — AUDITOR EDITORIAL (Paso 2: Filtro de Calidad y Coherencia)
# ──────────────────────────────────────────────
AUDITOR_SYSTEM_PROMPT = (
    "Eres el Director Editorial más exigente y veterano de contenido viral para YouTube Shorts y TikTok. "
    "Tu doble misión sagrada es: '1. NUNCA ABURRIR A LA AUDIENCIA (cero temas fríos, secos o burocráticos). 2. COHERENCIA LÓGICA IMPECABLE'. "
    "Tu trabajo es auditar despiadadamente los borradores de los guionistas. "
    "Si una historia es aburrida, sosa, le falta chispa o tiene contradicciones lógicas, "
    "la RECHAZAS de inmediato y señalas qué le falta para atrapar a la gente desde el segundo 1. "
    "Solo APRUEBAS cuando la historia es emocionante, adictiva, 100% lógica y atrapa como un imán. "
    "REGLAS CRÍTICAS: Cero emojis. Cero markdown. Solo texto corrido. Prohibida la palabra 'relatos'."
)

AUDITOR_CRITERIA_PROMPT = {
    "mystery": (
        "Audita este borrador de misterio/suspenso:\n\"\"\"{draft_script}\"\"\"\nTítulo propuesto: {draft_title}\n\n"
        "Evalúa con lupa:\n"
        "1. ¿El gancho (0 a 3s) atrapa como un imán sin preámbulos?\n"
        "2. ¿Tiene coherencia lógica interna? ¿Las acciones y pistas tienen causa y efecto real?\n"
        "3. ¿El giro final encaja de forma lógica y deja escalofríos?\n"
        "4. ¿Tiene entre 120 y 140 palabras exactas (38-45 segundos)?\n\n"
        "Si la historia carece de lógica o no atrapa, responde estrictamente:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Explica exactamente el fallo lógico o de entretenimiento]\n"
        "INSTRUCCIONES: [Qué debe cambiar el autor para que sea fascinante y lógica]\n\n"
        "Si la historia es coherente, intrigante y sólida, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [Guión final perfeccionado en prosa continua]\n"
        "TITULO: [Título viral sin emojis, máximo 50 caracteres]"
    ),
    "reddit": (
        "Audita esta historia de Reddit:\n\"\"\"{draft_script}\"\"\"\nTítulo propuesto: {draft_title}\n\n"
        "Filtro despiadado de calidad y entretenimiento:\n"
        "1. ¿ES REALMENTE ENTRETENIDA Y ADICTIVA? Si el tema es aburrido (economía, contabilidad, hojas de cálculo, papeleo laboral o tecnicismos fríos) o carece de tensión humana, RECHÁZALA DE INMEDIATO. Debe ser un drama o chisme apasionante.\n"
        "2. ¿El gancho (primeras 2 líneas) suelta una bomba que obliga a quedarse hasta el final?\n"
        "3. ¿Tiene coherencia lógica y humana? ¿Las motivaciones y reacciones son verosímiles?\n"
        "4. ¿El conflicto y desenlace son claros, emocionantes o de dulce revancha?\n"
        "5. ¿Tiene entre 120 y 140 palabras exactas?\n\n"
        "Si es aburrida, sosa, o carece de coherencia, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Por qué es aburrida o dónde falla la lógica]\n"
        "INSTRUCCIONES: [Cómo hacerla entretenida, vibrante y coherente]\n\n"
        "Si es súper entretenida, coherente y lista para viralizarse, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [Guión final perfeccionado en prosa continua]\n"
        "TITULO: [Título viral sin emojis, máximo 50 caracteres]"
    ),
    "bizarre": (
        "Audita esta historia de situaciones bizarras / gente loca / desastres épicos:\n\"\"\"{draft_script}\"\"\"\nTítulo propuesto: {draft_title}\n\n"
        "Filtro de retención y adicción:\n"
        "1. ¿Provoca asombro o risa incrédula de inmediato? Cero tecnicismos ni aburrimiento.\n"
        "2. ¿El gancho (0 a 3s) describe una situación tan descarada que nadie puede dejar de escuchar?\n"
        "3. ¿La resolución de karma o desastre es clara y satisfactoria?\n"
        "4. ¿Tiene entre 120 y 140 palabras exactas?\n\n"
        "Si es tibia, aburrida o incoherente, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Por qué no atrapa o qué le falta]\n"
        "INSTRUCCIONES: [Cómo subirle la intensidad y el karma]\n\n"
        "Si es atrapante y sensacional, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [Guión final perfeccionado en prosa continua]\n"
        "TITULO: [Título viral sin emojis, máximo 50 caracteres]"
    ),
    "news": (
        "Audita este resumen informativo:\n\"\"\"{draft_script}\"\"\"\nTítulo propuesto: {draft_title}\n\n"
        "Evalúa con lupa:\n"
        "1. ¿Es riguroso, insólito y entretenido? Cero política ni economía.\n"
        "2. ¿El gancho es un dato desconcertante?\n"
        "3. Longitud: entre 120 y 140 palabras.\n\n"
        "Si tiene datos vagos o aburridos, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Detalle del fallo]\n"
        "INSTRUCCIONES: [Qué corregir]\n\n"
        "Si es excelente, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [Guión final en prosa continua]\n"
        "TITULO: [Título viral sin emojis, máximo 50 caracteres]"
    ),
}

USER_PROMPTS = {
    "mystery": (
        "Escribe una historia de terror y suspenso con COHERENCIA LÓGICA TOTAL para YouTube Shorts y TikTok.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. GANCHO BRUTAL (0 a 3s): Comienza con un hecho aterrador y concreto sin preámbulos.\n"
        "2. ESCALADA LÓGICA: Cada pista debe ser coherente con la anterior.\n"
        "3. MICRO-HOOK (segundo 15): Reengancha la curiosidad con una frase de quiebre.\n"
        "4. GIRO FINAL COHERENTE E INFINITE LOOP: El desenlace revela la verdad y conecta sutilmente con la primera frase.\n"
        "5. EXTENSIÓN: Entre 120 y 140 palabras exactas.\n"
        "6. CERO EMOJIS ni markdown. Solo prosa fluida.\n\n"
        "TITULO: [Título viral sin emojis, máximo 50 caracteres]"
    ),
    "reddit": (
        "Escribe una historia viral de Reddit adictiva, entretenida y con gancho brutal (drama familiar, secretos inconfesables, venganza épica contra alguien tóxico, o situación social incómoda llevada al límite).\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "- CERO TEMAS ABURRIDOS: Prohibido hablar de economía, finanzas, hojas de cálculo, contabilidad, contratos o burocracia laboral.\n"
        "- GANCHO BRUTAL (0 a 3s): La primera frase debe soltar una bomba que impida deslizar el video.\n"
        "- MICRO-HOOK (segundo 15): Reengancha la tensión con un giro o revelación.\n"
        "- Narrada en primera persona con tono conversacional de chisme real y apasionado.\n"
        "- Desenlace satisfactorio y frase final que cierre en Infinite Loop.\n"
        "- Entre 120 y 140 palabras exactas.\n"
        "- CERO EMOJIS ni formato markdown. Solo prosa fluida.\n\n"
        "TITULO: [Título irresistible sin emojis, máximo 50 caracteres]"
    ),
    "bizarre": (
        "Escribe una historia bizarra o desastre social de la vida real (estilo r/trashy, r/tifu, desastres épicos, karma instantáneo a gente sinvergüenza).\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "- GANCHO FEROZ (0 a 3s): Empieza describiendo el acto más descarado o vergonzoso posible.\n"
        "- TONO: Irónico, adictivo, como contándole la mayor locura de tu barrio a un amigo.\n"
        "- MICRO-HOOK (segundo 15): La situación empeora o se destapa la verdad en público.\n"
        "- DESENLACE: Karma dulce, humillación justa o final surrealista con Infinite Loop.\n"
        "- Entre 120 y 140 palabras exactas.\n"
        "- CERO EMOJIS ni formato markdown. Solo prosa fluida.\n\n"
        "TITULO: [Título impactante sin emojis, máximo 50 caracteres]"
    ),
    "news": (
        "Escribe un guión de curiosidad insólita real para YouTube Shorts.\n\n"
        "REGLAS:\n"
        "- CERO TEMAS POLÍTICOS O ECONÓMICOS. Solo misterios reales o ciencia asombrosa.\n"
        "- Entre 120 y 135 palabras.\n"
        "- Comienza con un dato desconcertante.\n"
        "- CERO EMOJIS ni formato markdown.\n\n"
        "TITULO: [Título impactante sin emojis, máximo 50 caracteres]"
    ),
}


def _get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY no configurada en .env")
    return Groq(api_key=key, max_retries=1)


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


def _parse_auditor_response(raw: str, default_title: str) -> Dict[str, Any]:
    """Parsea la respuesta del Auditor para determinar si está APROBADO o RECHAZADO."""
    cleaned = _clean(raw)
    upper = cleaned.upper()

    is_approved = "ESTADO: APROBADO" in upper or "ESTADO:APROBADO" in upper

    # Extraer guión
    script = ""
    title = default_title
    criticism = ""
    instructions = ""

    if "GUION:" in upper:
        parts = re.split(r"GUION:\s*", cleaned, flags=re.IGNORECASE)
        if len(parts) > 1:
            rest = parts[1]
            if "TITULO:" in rest.upper():
                t_parts = re.split(r"TITULO:\s*", rest, flags=re.IGNORECASE)
                script = t_parts[0].strip()
                title = t_parts[1].split("\n")[0].strip()
            else:
                script = rest.strip()
    elif is_approved:
        script, title = _parse_script_and_title(cleaned, default_title)

    if not is_approved:
        if "CRITICA:" in upper:
            c_part = re.split(r"CRITICA:\s*", cleaned, flags=re.IGNORECASE)[1]
            if "INSTRUCCIONES:" in c_part.upper():
                criticism = re.split(r"INSTRUCCIONES:\s*", c_part, flags=re.IGNORECASE)[0].strip()
                instructions = re.split(r"INSTRUCCIONES:\s*", c_part, flags=re.IGNORECASE)[1].strip()
            else:
                criticism = c_part.strip()
        else:
            criticism = cleaned[:300]

    return {
        "approved": is_approved,
        "script": remove_emojis(_clean(script)),
        "title": remove_emojis(_clean(title))[:60],
        "criticism": criticism,
        "instructions": instructions,
        "raw": cleaned,
    }


def _call_llm(client: Groq, system_msg: str, user_msg: str, temperature: float = 0.8, max_tokens: int = 350) -> str:
    """Invoca LLM probando modelos rápidos en cascada con fallback robusto a Gemini."""
    # 1. Intentar con modelos en Groq
    groq_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
    for model_name in groq_models:
        try:
            r = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
                max_tokens=min(max_tokens, 380),
            )
            content = r.choices[0].message.content
            if content and len(content.strip()) > 30:
                return _clean(content)
        except Exception as e:
            logger.warning("Aviso en modelo Groq %s: %s. Probando alternativa...", model_name, str(e)[:120])

    # 2. Fallback resiliente a Gemini (probando 2.5-flash, 2.0-flash y 2.0-flash-lite)
    gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    for g_model in gemini_models:
        try:
            gemini_c = _get_gemini_client()
            res = gemini_c.models.generate_content(
                model=g_model,
                contents=f"{system_msg}\n\n{user_msg}",
            )
            if res.text and len(res.text.strip()) > 30:
                logger.info("Respuesta obtenida con éxito usando fallback Gemini (%s)", g_model)
                return _clean(res.text)
        except Exception as eg:
            logger.warning("Aviso en modelo Gemini %s: %s. Probando siguiente...", g_model, str(eg)[:120])

    raise RuntimeError("Todos los motores de IA fallaron al generar respuesta.")


def _audit_and_evaluate_draft(
    draft_script: str,
    draft_title: str,
    module_type: str,
    client: Groq,
    is_final_round: bool = False,
) -> Dict[str, Any]:
    """Paso Auditor: Evalúa la coherencia lógica de la historia y aprueba o rechaza con críticas específicas."""
    criteria = AUDITOR_CRITERIA_PROMPT.get(module_type, AUDITOR_CRITERIA_PROMPT["mystery"]).format(
        draft_script=draft_script,
        draft_title=draft_title,
    )

    if is_final_round:
        criteria += (
            "\n\nATENCIÓN: Esta es la RONDA FINAL. Si la historia aún tiene pequeñas fallas, "
            "tú mismo como Director Editorial REESCRIBE Y PULE el guión definitivo con lógica impecable "
            "y respóndelo inmediatamente como ESTADO: APROBADO con el GUION y TITULO listos."
        )

    raw_response = _call_llm(
        client=client,
        system_msg=AUDITOR_SYSTEM_PROMPT,
        user_msg=criteria,
        temperature=0.65,
        max_tokens=850,
    )

    return _parse_auditor_response(raw_response, draft_title)


def _regenerate_with_criticism(
    previous_script: str,
    criticism: str,
    instructions: str,
    module_type: str,
    client: Groq,
) -> tuple[str, str]:
    """El Generador reescribe la historia corrigiendo específicamente las fallas lógicas marcadas por el Auditor."""
    sys_prompt = SYSTEM_PROMPTS.get(module_type, SYSTEM_PROMPTS["mystery"])
    user_prompt = (
        f"El Director Editorial RECHAZÓ tu borrador anterior por falta de coherencia lógica:\n\n"
        f"BORRADOR ANTERIOR:\n\"\"\"{previous_script}\"\"\"\n\n"
        f"FALLOS DETECTADOS POR EL AUDITOR:\n{criticism}\n\n"
        f"INSTRUCCIONES DE CORRECCIÓN:\n{instructions}\n\n"
        f"Reescribe la historia desde cero corrigiendo cada falla. "
        f"La causa y efecto debe ser 100% lógica, humana y verosímil. "
        f"Extensión estricta: entre 135 y 155 palabras. CERO emojis. Cero markdown.\n"
        f"Al final incluye: TITULO: [título viral sin emojis]"
    )

    raw_new = _call_llm(
        client=client,
        system_msg=sys_prompt,
        user_msg=user_prompt,
        temperature=0.82,
        max_tokens=650,
    )
    return _parse_script_and_title(raw_new)


def generate_script(
    module_type: str,
    extra_context: Optional[str] = None,
    **kwargs,
) -> Dict[str, str]:
    """Genera guión usando un LOOP INTERACTIVO DUAL DE IA (Generador <-> Auditor):
    1. IA Generadora crea el borrador.
    2. IA Auditora evalúa coherencia lógica, gancho y categoría.
    3. Si el Auditor rechaza, la IA Generadora corrige los fallos específicos.
    4. Se itera hasta que el Auditor emita 'ESTADO: APROBADO' (máximo 3 rondas).
    """
    if module_type not in SYSTEM_PROMPTS:
        raise ValueError(f"Módulo desconocido: {module_type}")

    client = _get_groq_client()
    sys_prompt = SYSTEM_PROMPTS[module_type]
    user_prompt = USER_PROMPTS[module_type]

    if module_type == "news" and extra_context:
        user_prompt += f"\n\nContexto de la noticia: {extra_context}"
    elif module_type == "reddit" and extra_context:
        user_prompt += f"\n\nHistoria base de Reddit: {extra_context}"
    elif module_type == "bizarre" and extra_context:
        user_prompt += f"\n\nHistoria base insólita/bizarra: {extra_context}"

    # ── RONDA 1: Generación inicial ──────────────────────────────────────────
    logger.info("=== [DUAL-AI LOOP] Iniciando generación y filtro de coherencia — Categoría: %s ===", module_type.upper())
    logger.info("[Ronda 1] IA Generadora creando propuesta inicial...")

    raw_initial = _call_llm(client, sys_prompt, user_prompt, temperature=0.90, max_tokens=600)
    current_script, current_title = _parse_script_and_title(raw_initial)
    logger.info("[Ronda 1] Borrador inicial listo (%d palabras): '%s'", len(current_script.split()), current_title)

    max_rounds = 3
    final_script = current_script
    final_title = current_title

    for round_num in range(1, max_rounds + 1):
        is_final = (round_num == max_rounds)
        logger.info("[Ronda %d/%d] IA Auditora evaluando coherencia lógica y categoría...", round_num, max_rounds)

        audit = _audit_and_evaluate_draft(
            draft_script=current_script,
            draft_title=current_title,
            module_type=module_type,
            client=client,
            is_final_round=is_final,
        )

        if audit["approved"] and len(audit["script"].split()) >= 80:
            logger.info("✓ [DUAL-AI APROBADO] El Auditor aprobó la historia en la ronda %d!", round_num)
            final_script = audit["script"]
            final_title = audit["title"] or current_title
            break

        if not is_final:
            logger.warning(
                "✗ [Ronda %d RECHAZADA] Auditor detectó falta de coherencia: %s",
                round_num,
                audit["criticism"][:150] + "..." if len(audit["criticism"]) > 150 else audit["criticism"],
            )
            logger.info("[Ronda %d] IA Generadora reescribiendo y corrigiendo lógica...", round_num + 1)
            current_script, current_title = _regenerate_with_criticism(
                previous_script=current_script,
                criticism=audit["criticism"],
                instructions=audit["instructions"],
                module_type=module_type,
                client=client,
            )
        else:
            # En ronda final, si el script devuelto por el auditor es válido, tomarlo
            if audit["script"] and len(audit["script"].split()) >= 80:
                final_script = audit["script"]
                final_title = audit["title"] or current_title
            else:
                final_script = current_script
                final_title = current_title
            logger.info("✓ [DUAL-AI FINAL] Finalizado ciclo de auditoría.")

    final_script = remove_emojis(_clean(final_script))
    final_title = remove_emojis(_clean(final_title))[:60]

    logger.info(
        "=== [DUAL-AI ÉXITO] Guión verificado y aprobado: %d palabras | Título: '%s' ===",
        len(final_script.split()),
        final_title,
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
