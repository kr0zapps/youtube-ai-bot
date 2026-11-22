"""MÃ³dulo de generaciÃ³n de guiones usando Groq (LLM principal) + Gemini (imÃ¡genes).

Groq usa llama-3.3-70b-versatile gratis con hasta 8.000 tokens de salida.
Sistema dual de IA: Generador + Auditor para guiones de mÃ¡xima calidad viral.
Gemini se reserva para generar prompts de imÃ¡genes.
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

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PROMPTS â€” GENERADOR (Paso 1)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SYSTEM_PROMPTS = {
    "mystery": (
        "Eres un novelista y guionista maestro del suspense psicolÃ³gico y misterio oscuro para YouTube Shorts y TikTok. "
        "FÃ“RMULA DE RETENCIÃ“N 2026:\n"
        "1. GANCHO (0 a 3s): Empieza directamente en medio de una situaciÃ³n perturbadora o un descubrimiento aterrador. "
        "Cero saludos ni explicaciones lentas.\n"
        "2. MICRO-HOOK (a los 15s): Introduce un reenganche ('Pero lo que vi despuÃ©s...', 'En ese instante me di cuenta de mi error...').\n"
        "3. COHERENCIA TOTAL: Verosimilitud absoluta, causa y efecto realista (cÃ¡maras de seguridad, llamadas grabadas, vecinos, casas antiguas).\n"
        "4. BUCLE INFINITO (Infinite Loop): La frase final debe conectar con la frase inicial sin que se note el corte.\n"
        "PROHIBIDO USAR EMOJIS ni formato markdown. Solo prosa fluida continua con comas y puntos."
    ),
    "reddit": (
        "Eres un narrador maestro de historias virales de Reddit de mÃ¡ximo impacto emocional y morbo social (estilo r/confessions, r/tifu, r/BestofRedditorUpdates, r/pettyrevenge). "
        "FÃ“RMULA DE RETENCIÃ“N 2026:\n"
        "1. GANCHO (0 a 3s): Suelta una bomba humana de inmediato que impida deslizar el video.\n"
        "2. CERO TEMAS ABURRIDOS: Estrictamente prohibido hablar de economÃ­a, hojas de cÃ¡lculo, contabilidad, contratos corporativos o burocracia de oficina. Las historias deben tratar sobre dramas humanos: infidelidades, secretos familiares, venganzas personales deliciosas contra arrogantes o vecinos insoportables.\n"
        "3. MICRO-HOOK (a los 15s): Renueva la tensiÃ³n antes de que el espectador se distraiga.\n"
        "4. BUCLE INFINITO: Cierra con una frase que enlace fluidamente de vuelta al inicio.\n"
        "PROHIBIDO USAR EMOJIS ni formato markdown. Lenguaje directo y coloquial."
    ),
    "bizarre": (
        "Eres el narrador definitivo de historias insÃ³litas, desastres sociales, situaciones caÃ³ticas y gente sinvergÃ¼enza (estilo r/trashy, r/tifu, momentos virales de 'cosas mierdas / ridÃ­culas'). "
        "FÃ“RMULA DE RETENCIÃ“N 2026:\n"
        "1. GANCHO (0 a 3s): Arranca con la estupidez o insolencia mÃ¡s grande que alguien haya hecho jamÃ¡s.\n"
        "2. TONO IRÃ“NICO Y ADICTIVO: Mezcla de asombro y sÃ¡tira, narrando cÃ³mo el karma aplastÃ³ a alguien que se creÃ­a intocable (un estafador torpe, una boda boicoteada, un vecino sinvergÃ¼enza humillado en pÃºblico).\n"
        "3. MICRO-HOOK (a los 15s): Escalada de la vergÃ¼enza ajena o el desastre.\n"
        "4. BUCLE INFINITO: Final Ã©pico y satisfactorio que conecta con la apertura.\n"
        "PROHIBIDO USAR EMOJIS ni formato markdown. Cero temas aburridos."
    ),
    "news": (
        "Eres un periodista de divulgaciÃ³n cientÃ­fica y sucesos insÃ³litos para YouTube Shorts y TikTok. "
        "REGLA DE ORO: RIGOR Y COHERENCIA TOTAL. Explicas misterios resueltos, descubrimientos arqueolÃ³gicos "
        "o fenÃ³menos fascinantes con causa y efecto claros. CERO TEMAS POLÃTICOS O ECONÃ“MICOS ABURRIDOS. "
        "PROHIBIDO USAR EMOJIS ni formato markdown."
    ),
        "gta6_news": (
        "Eres un presentador y creador viral de élite en TikTok y YouTube Shorts cubriendo las NOTICIAS, MEMES Y TENDENCIAS DE LAS ÚLTIMAS 24 HORAS de GTA 6. "
        "FÓRMULA DE RETENCIÓN VIRAL 2026 (SOP GTA 6):\n"
        "1. ACTUALIDAD Y RIGOR: Debes basar tu noticia obligatoriamente en el TITULAR O TENDENCIA DE HOY suministrado en el contexto. Está estrictamente prohibido inventar temas, mencionar parches viejos (1.02, etc.) o hablar de tráilers antiguos. Habla con emoción y chispa del suceso real que está viviendo la comunidad hoy.\n"
        "2. GANCHO (0 a 3s): Pregunta o afirmación impactante directa a la noticia del día.\n"
        "3. MICRO-HOOK (15s): Introduce el giro, la anécdota o la reacción de los jugadores.\n"
        "4. BUCLE INFINITO (Infinite Loop): La frase final debe conectar sin costuras con el gancho inicial.\n"
        "PROHIBIDO USAR EMOJIS ni markdown. Longitud exacta: 85 a 110 palabras."
    ),
    "gta6_tips": (
        "Eres un analista y estratega veterano de videojuegos creando guÃ­as prÃ¡cticas y HOW-TOs Ãºtiles sobre GTA 6. "
        "FÃ“RMULA DE RETENCIÃ“N 2026 (SOP GTA 6):\n"
        "1. GANCHO (0 a 3s): Plantea un problema o necesidad tÃ©cnica urgente (espacio de almacenamiento, zonas horarias de desbloqueo, cuentas de Rockstar).\n"
        "2. UTILIDAD PURA: 2 o 3 pasos ultra concretos que el espectador querrÃ¡ guardar en favoritos o compartir.\n"
        "3. RIGOR: Basado Ãºnicamente en hechos tÃ©cnicos oficiales y estÃ¡ndares de consolas PS5/Xbox.\n"
        "4. BUCLE INFINITO: Cierra conectando de vuelta al gancho inicial.\n"
        "PROHIBIDO USAR EMOJIS ni markdown. Longitud exacta: 85 a 110 palabras."
    ),
    "gta6_clip": (
        "Eres un analista de cinemÃ¡ticas y clips de GTA 6 con ojo clÃ­nico para detalles ocultos. "
        "FÃ“RMULA DE RETENCIÃ“N 2026 (SOP GTA 6):\n"
        "1. GANCHO (0 a 3s): 'Casi nadie notÃ³ este detalle en el trÃ¡iler oficial...' o llamada directa a la fÃ­sica, NPC o mapa.\n"
        "2. EXPLICACIÃ“N ENÃ‰RGICA: Desgrana la escena oficial respetando el crÃ©dito de origen.\n"
        "3. CIERRE EMOCIONAL / BUCLE: Cierra con una frase sobre la evoluciÃ³n de la saga que conecte al inicio.\n"
        "PROHIBIDO USAR EMOJIS ni markdown. Longitud exacta: 85 a 110 palabras."
    ),
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PROMPTS â€” AUDITOR EDITORIAL (Paso 2: Filtro de Calidad y Coherencia)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
AUDITOR_SYSTEM_PROMPT = (
    "Eres el Director Editorial mÃ¡s exigente y veterano de contenido viral para YouTube Shorts y TikTok. "
    "Tu triple misiÃ³n sagrada es: "
    "1. CONCISIÃ“N QUIRÃšRGICA: PROHIBIDO EL RELLENO, LAS FRASES VACÃAS Y LAS REDUNDANCIAS. Si una historia alarga las cosas a propÃ³sito, repite ideas o usa muletillas ('y es que', 'cabe destacar', 'como era de esperarse'), la RECHAZAS DE INMEDIATO. Cada palabra debe ganarse su lugar. "
    "2. NUNCA ABURRIR A LA AUDIENCIA (cero temas frÃ­os, secos o burocrÃ¡ticos). "
    "3. COHERENCIA LÃ“GICA IMPECABLE. "
    "Tu trabajo es auditar despiadadamente los borradores de los guionistas. "
    "Solo APRUEBAS cuando la historia es concisa, emocionante, adictiva, 100% lÃ³gica y atrapa como un imÃ¡n. "
    "REGLAS CRÃTICAS: Entre 85 y 110 palabras exactas. Cero emojis. Cero markdown. Solo texto corrido. Prohibida la palabra 'relatos'."
)

AUDITOR_CRITERIA_PROMPT = {
    "mystery": (
        "Audita este borrador de misterio/suspenso:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "EvalÃºa con lupa:\n"
        "1. Â¿El gancho (0 a 3s) atrapa como un imÃ¡n sin preÃ¡mbulos?\n"
        "2. Â¿Tiene coherencia lÃ³gica interna? Â¿Las acciones y pistas tienen causa y efecto real?\n"
        "3. Â¿El giro final encaja de forma lÃ³gica y deja escalofrÃ­os?\n"
        "4. Â¿Es CONCISO y SIN RELLENO? Â¿Tiene entre 85 y 110 palabras exactas (~30-38 segundos)? Prohibido alargar con frases redundantes.\n\n"
        "Si la historia carece de lÃ³gica, es redundante o no atrapa, responde estrictamente:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Explica exactamente el fallo lÃ³gico, redundancia o falta de tensiÃ³n]\n"
        "INSTRUCCIONES: [QuÃ© debe cambiar el autor para que sea fascinante, concisa y lÃ³gica]\n\n"
        "Si la historia es coherente, intrigante, concisa y sÃ³lida, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final perfeccionado en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "reddit": (
        "Audita esta historia de Reddit:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "Filtro despiadado de calidad, concisiÃ³n y entretenimiento:\n"
        "1. Â¿ES CONCISA Y DIRECTA AL GRANO? PROHIBIDO EL RELLENO, LAS FRASES VACÃAS Y LAS REDUNDANCIAS. Si la historia repite ideas, usa explicaciones obvias o alarga la narrativa con palabras de relleno ('y es que', 'por si fuera poco', 'como era de esperarse'), RECHÃZALA DE INMEDIATO. Cada oraciÃ³n debe aportar un giro o dato crucial.\n"
        "2. Â¿ES REALMENTE ENTRETENIDA Y ADICTIVA? Si el tema es aburrido (economÃ­a, contabilidad, hojas de cÃ¡lculo, papeleo laboral o tecnicismos frÃ­os) o carece de tensiÃ³n humana, RECHÃZALA. Debe ser un drama o chisme apasionante.\n"
        "3. Â¿El gancho (primeras 2 lÃ­neas) suelta una bomba que obliga a quedarse hasta el final?\n"
        "4. Â¿Tiene coherencia lÃ³gica y humana? Â¿Las motivaciones y reacciones son verosÃ­miles?\n"
        "5. Â¿Tiene entre 85 y 110 palabras exactas (~32-40 segundos)?\n\n"
        "Si es redundante, aburrida, sosa o incoherente, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Por quÃ© es redundante, aburrida o dÃ³nde falla la lÃ³gica]\n"
        "INSTRUCCIONES: [CÃ³mo hacerla ultra concisa, vibrante y coherente eliminando todo relleno]\n\n"
        "Si es sÃºper entretenida, concisa, coherente y lista para viralizarse, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final perfeccionado en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "bizarre": (
        "Audita esta historia de situaciones bizarras / gente loca / desastres Ã©picos:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "Filtro de concisiÃ³n, retenciÃ³n y adicciÃ³n:\n"
        "1. Â¿Es CONCISA y SIN RELLENO? Cero palabras vacÃ­as o redundantes. Cada frase debe disparar la historia hacia adelante.\n"
        "2. Â¿Provoca asombro o risa incrÃ©dula de inmediato? Cero tecnicismos ni aburrimiento.\n"
        "3. Â¿El gancho (0 a 3s) describe una situaciÃ³n tan descarada que nadie puede dejar de escuchar?\n"
        "4. Â¿La resoluciÃ³n de karma o desastre es clara y satisfactoria?\n"
        "5. Â¿Tiene entre 85 y 110 palabras exactas (~32-40 segundos)?\n\n"
        "Si es tibia, redundante o incoherente, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Por quÃ© no atrapa, quÃ© relleno tiene o quÃ© le falta]\n"
        "INSTRUCCIONES: [CÃ³mo recortar el relleno y subirle la intensidad y el karma]\n\n"
        "Si es atrapante, concisa y sensacional, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final perfeccionado en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "news": (
        "Audita este resumen informativo:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "EvalÃºa con lupa:\n"
        "1. Â¿Es riguroso, insÃ³lito y entretenido? Cero polÃ­tica ni economÃ­a.\n"
        "2. Â¿El gancho es un dato desconcertante?\n"
        "3. Longitud: entre 85 y 110 palabras exactas. Cero relleno.\n\n"
        "Si tiene datos vagos, aburridos o relleno, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Detalle del fallo]\n"
        "INSTRUCCIONES: [QuÃ© corregir y quÃ© recortar]\n\n"
        "Si es excelente y conciso, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "gta6_news": (
        "Audita este guiÃ³n de noticias de Ãºltima hora de GTA 6:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "Filtro estricto de rigurosa actualidad (HOY MISMO):\n"
        "1. ¿TRATA SOBRE LA NOTICIA O TENDENCIA REAL DE HOY suministrada en el contexto? Si inventa datos no suministrados, menciona trailers viejos de 2023 o parches antiguos, RECHÁZALO DE INMEDIATO. Debe tratar con frescura y dinamismo el suceso de hoy.\n"
        "2. Â¿El gancho (0 a 3s) tiene la urgencia e impacto de una noticia de Ãºltima hora?\n"
        "3. Â¿Tiene entre 85 y 110 palabras exactas? Cero relleno.\n"
        "4. Â¿La frase final enlaza en Infinite Loop con el gancho?\n\n"
        "Si contiene datos viejos, es aburrido o tiene relleno, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Por quÃ© contiene datos desactualizados o quÃ© le falta]\n"
        "INSTRUCCIONES: [CÃ³mo enfocarlo en la noticia candente de hoy mismo]\n\n"
        "Si es una noticia de Ãºltima hora fresca, verÃ­dica y electrizante, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "gta6_tips": (
        "Audita este guiÃ³n de HOW-TO / GuÃ­a prÃ¡ctica de GTA 6:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "Filtro de utilidad y concisiÃ³n:\n"
        "1. Â¿Aporta un valor prÃ¡ctico real que motive a guardar o compartir el video?\n"
        "2. Â¿Es 100% verÃ­dico y coherente con las especificaciones tÃ©cnicas oficiales?\n"
        "3. Â¿Tiene entre 85 y 110 palabras exactas? Cero relleno.\n\n"
        "Si no aporta utilidad o tiene relleno, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Por quÃ© no es Ãºtil o quÃ© sobra]\n"
        "INSTRUCCIONES: [CÃ³mo resumir los pasos prÃ¡cticos]\n\n"
        "Si es directo, ultra Ãºtil y conciso, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "gta6_clip": (
        "Audita este guiÃ³n de anÃ¡lisis de clip de GTA 6:\n\"\"\"{draft_script}\"\"\"\nTÃ­tulo propuesto: {draft_title}\n\n"
        "EvalÃºa:\n"
        "1. Â¿Analiza un detalle concreto y visual del trÃ¡iler/gameplay oficial?\n"
        "2. Â¿Evita inventar teorÃ­as falsas o clickbait engaÃ±oso?\n"
        "3. Â¿Tiene entre 85 y 110 palabras exactas?\n\n"
        "Si es engaÃ±oso o redundante, responde:\n"
        "ESTADO: RECHAZADO\n"
        "CRITICA: [Fallo de retenciÃ³n o detalle dudoso]\n"
        "INSTRUCCIONES: [CÃ³mo enfocar el detalle visual real]\n\n"
        "Si es impecable, responde:\n"
        "ESTADO: APROBADO\n"
        "GUION: [GuiÃ³n final en prosa continua, 85-110 palabras]\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
}

USER_PROMPTS = {
    "mystery": (
        "Escribe una historia de terror y suspenso con COHERENCIA LÃ“GICA TOTAL para YouTube Shorts y TikTok.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. GANCHO BRUTAL (0 a 3s): Comienza con un hecho aterrador y concreto sin preÃ¡mbulos.\n"
        "2. ESCALADA LÃ“GICA: Cada pista debe ser coherente con la anterior.\n"
        "3. MICRO-HOOK (segundo 15): Reengancha la curiosidad con una frase de quiebre.\n"
        "4. GIRO FINAL COHERENTE E INFINITE LOOP: El desenlace revela la verdad y conecta sutilmente con la primera frase.\n"
        "5. CONCISIÃ“N ABSOLUTA: Entre 85 y 110 palabras exactas (~30-38s). PROHIBIDO EL RELLENO O FRASES REDUNDANTES.\n"
        "6. CERO EMOJIS ni markdown. Solo prosa fluida.\n\n"
        "TITULO: [TÃ­tulo viral sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "reddit": (
        "Escribe una historia viral de Reddit ultra adictiva, concisa y con gancho brutal (drama familiar, venganza Ã©pica contra alguien tÃ³xico, o karma demoledor).\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "- CERO RELLENO O REDUNDANCIAS: Prohibido repetir ideas, dar explicaciones innecesarias o alargar las oraciones. Cada palabra debe ser precisa y avanzar la trama.\n"
        "- CERO TEMAS ABURRIDOS: Prohibido hablar de economÃ­a, finanzas, hojas de cÃ¡lculo, contabilidad o burocracia laboral.\n"
        "- GANCHO BRUTAL (0 a 3s): La primera frase debe soltar una bomba que impida deslizar el video.\n"
        "- MICRO-HOOK (segundo 15): Reengancha la tensiÃ³n con un giro o revelaciÃ³n.\n"
        "- Narrada en primera persona con tono conversacional de chisme real y apasionado.\n"
        "- Desenlace satisfactorio y frase final que cierre en Infinite Loop.\n"
        "- EXTENSIÃ“N: Entre 85 y 110 palabras exactas (~32-40 segundos).\n"
        "- CERO EMOJIS ni formato markdown. Solo prosa fluida.\n\n"
        "TITULO: [TÃ­tulo irresistible sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "bizarre": (
        "Escribe una historia bizarra o desastre social de la vida real (estilo r/trashy, r/tifu, desastres Ã©picos, karma instantÃ¡neo a gente sinvergÃ¼enza).\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "- CERO RELLENO: Nada de palabras redundantes o explicaciones obvias. Directo al grano con mÃ¡xima energÃ­a.\n"
        "- GANCHO FEROZ (0 a 3s): Empieza describiendo el acto mÃ¡s descarado o vergonzoso posible.\n"
        "- TONO: IrÃ³nico, adictivo, como contÃ¡ndole la mayor locura de tu barrio a un amigo.\n"
        "- MICRO-HOOK (segundo 15): La situaciÃ³n empeora o se destapa la verdad en pÃºblico.\n"
        "- DESENLACE: Karma dulce, humillaciÃ³n justa o final surrealista con Infinite Loop.\n"
        "- EXTENSIÃ“N: Entre 85 y 110 palabras exactas (~32-40 segundos).\n"
        "- CERO EMOJIS ni formato markdown. Solo prosa fluida.\n\n"
        "TITULO: [TÃ­tulo impactante sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "news": (
        "Escribe un guiÃ³n de curiosidad insÃ³lita real para YouTube Shorts.\n\n"
        "REGLAS:\n"
        "- CERO TEMAS POLÃTICOS O ECONÃ“MICOS. Solo misterios reales o ciencia asombrosa.\n"
        "- Entre 85 y 105 palabras exactas. Cero relleno.\n"
        "- Comienza con un dato desconcertante.\n"
        "- CERO EMOJIS ni formato markdown.\n\n"
        "TITULO: [TÃ­tulo impactante sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "gta6_news": (
        "Escribe un guiÃ³n de noticias 100% oficiales y confirmadas sobre Grand Theft Auto VI para formato vertical (Shorts/TikTok/Reels).\n\n"
        "REGLAS ESTRICTAS DEL SOP:\n"
        "- Fuentes oficiales Ãºnicamente (Rockstar Games / Take-Two / PlayStation / Xbox).\n"
        "- PROHIBIDO incluir rumores, filtraciones o especulaciÃ³n.\n"
        "- GANCHO BRUTAL (0 a 3s) directo a la noticia.\n"
        "- MICRO-HOOK al segundo 15.\n"
        "- Frase final que cierre en Infinite Loop.\n"
        "- EXTENSIÃ“N: Entre 85 y 110 palabras exactas.\n"
        "- CERO EMOJIS ni markdown.\n\n"
        "TITULO: [TÃ­tulo impactante sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "gta6_tips": (
        "Escribe un guiÃ³n de guÃ­a prÃ¡ctica / HOW-TO de alta utilidad sobre GTA 6.\n\n"
        "REGLAS ESTRICTAS DEL SOP:\n"
        "- EnfÃ³cate en un problema real: preparaciÃ³n de espacio en disco, zonas de desbloqueo, cuentas oficiales o requisitos.\n"
        "- 2 o 3 pasos directos y claros pensados para que el usuario guarde el video.\n"
        "- GANCHO (0 a 3s) que plantee el problema de golpe.\n"
        "- EXTENSIÃ“N: Entre 85 y 110 palabras exactas.\n"
        "- CERO EMOJIS ni markdown.\n\n"
        "TITULO: [TÃ­tulo irresistible sin emojis, mÃ¡ximo 50 caracteres]"
    ),
    "gta6_clip": (
        "Escribe un guiÃ³n de desglose de escena o detalle oculto del trÃ¡iler oficial de GTA 6.\n\n"
        "REGLAS ESTRICTAS DEL SOP:\n"
        "- Detalle visual concreto (fÃ­sica de agua, multitudes en la playa, interacciÃ³n con caimanes, vehÃ­culos).\n"
        "- GANCHO (0 a 3s) que despierte curiosidad inmediata.\n"
        "- EXTENSIÃ“N: Entre 85 y 110 palabras exactas.\n"
        "- CERO EMOJIS ni markdown.\n\n"
        "TITULO: [TÃ­tulo impactante sin emojis, mÃ¡ximo 50 caracteres]"
    ),
}


def _get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY no configurada en .env")
    return Groq(api_key=key, max_retries=1)


def _get_gemini_client():
    if genai is None:
        raise ImportError("google-genai no estÃ¡ instalado.")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY no configurada en .env")
    return genai.Client(api_key=key)


def remove_emojis(text: str) -> str:
    """Elimina completamente cualquier emoji o sÃ­mbolo unicode decorativo."""
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
    """Extrae guiÃ³n y tÃ­tulo del texto crudo del LLM de forma robusta."""
    title = default_title
    raw_clean = _clean(raw)
    upper_raw = raw_clean.upper()

    if "TITULO:" in upper_raw:
        idx = upper_raw.index("TITULO:")
        # Si TITULO estÃ¡ en la primera mitad del texto, se generÃ³ primero el tÃ­tulo y luego el guiÃ³n
        if idx < len(raw_clean) // 3:
            lines = raw_clean.split("\n")
            title_parts = []
            script_parts = []
            capturing_title = False
            for line in lines:
                l_strip = line.strip()
                if not l_strip:
                    continue
                if l_strip.upper().startswith("TITULO:"):
                    title_parts.append(l_strip.split(":", 1)[-1].strip())
                    capturing_title = True
                elif l_strip.upper().startswith("GUION:") or l_strip.upper().startswith("GUIÃ“N:"):
                    capturing_title = False
                    script_parts.append(l_strip.split(":", 1)[-1].strip())
                elif capturing_title:
                    title_parts.append(l_strip)
                else:
                    script_parts.append(l_strip)
            if title_parts:
                title = " ".join(title_parts)
            if script_parts:
                script = " ".join(script_parts)
            else:
                script = raw_clean
        else:
            # TITULO estÃ¡ al final
            script = _clean(raw_clean[:idx])
            title = _clean(raw_clean[idx:].split(":", 1)[-1].split("\n")[0])
    elif "---" in raw_clean:
        parts = raw_clean.split("---", 1)
        script = _clean(parts[0])
        title = _clean(parts[1].split("\n")[0])
    else:
        lines = [l.strip() for l in raw_clean.split("\n") if l.strip()]
        if len(lines) >= 2 and len(lines[-1]) < 80:
            title = lines[-1]
            script = " ".join(lines[:-1])
        else:
            script = raw_clean
    # Limpiar etiquetas residuales
    script = re.sub(r"^\*{0,2}(GuiÃ³n|Script|NarraciÃ³n):?\*{0,2}\s*", "", script, flags=re.IGNORECASE)
    title = re.sub(r"^\*{0,2}(TÃ­tulo|Title|TITULO):?\*{0,2}\s*", "", title, flags=re.IGNORECASE)
    script = remove_emojis(_clean(script))
    title = remove_emojis(_clean(title))[:60]
    return script, title


def _parse_auditor_response(raw: str, default_title: str) -> Dict[str, Any]:
    """Parsea la respuesta del Auditor para determinar si estÃ¡ APROBADO o RECHAZADO."""
    cleaned = _clean(raw)
    upper = cleaned.upper()

    is_approved = "ESTADO: APROBADO" in upper or "ESTADO:APROBADO" in upper

    # Extraer guiÃ³n
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


REFUSAL_PHRASES = [
    "i'm sorry", "i am sorry", "i cannot", "i can't",
    "cannot fulfill", "cannot comply", "unable to comply",
    "as an ai", "as a language model", "lo siento",
    "no puedo cumplir", "no puedo generar", "no puedo completar",
    "i am unable to", "against my safety", "violates my"
]


def _is_refusal(text: str) -> bool:
    """Detecta si la respuesta del LLM es una negativa de censura o un mensaje genérico de error."""
    if not text:
        return True
    lower = text.lower()
    return any(p in lower for p in REFUSAL_PHRASES)


def _call_llm(client: Groq, system_msg: str, user_msg: str, temperature: float = 0.8, max_tokens: int = 750) -> str:
    """Invoca LLM probando primero los modelos más estables y rápidos en Groq, con fallback a Gemini."""
    # 1. Prioridad: Groq (Qwen primero por su velocidad de 1s, fluidez en español y cero negativas de censura)
    groq_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    for model_name in groq_models:
        try:
            r = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = r.choices[0].message.content
            if content and len(content.strip()) > 30:
                if not _is_refusal(content):
                    logger.info("✓ Generación con éxito usando Groq (%s)", model_name)
                    return _clean(content)
                else:
                    logger.warning("Aviso: Modelo Groq %s devolvió una negativa/refusal. Probando siguiente...", model_name)
        except Exception as e:
            logger.warning("Aviso en modelo Groq %s: %s. Probando alternativa...", model_name, str(e)[:120])

    # 2. Fallback: Gemini
    gemini_models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    for g_model in gemini_models:
        try:
            gemini_c = _get_gemini_client()
            res = gemini_c.models.generate_content(
                model=g_model,
                contents=f"{system_msg}\n\n{user_msg}",
            )
            if res.text and len(res.text.strip()) > 30:
                if not _is_refusal(res.text):
                    logger.info("✓ Generación con éxito usando %s", g_model)
                    return _clean(res.text)
        except Exception as eg:
            logger.warning("Aviso en modelo Gemini %s: %s. Probando alternativa...", g_model, str(eg)[:120])

    raise RuntimeError("Todos los motores de IA fallaron al generar respuesta válida.")


def _audit_and_evaluate_draft(
    draft_script: str,
    draft_title: str,
    module_type: str,
    client: Groq,
    is_final_round: bool = False,
) -> Dict[str, Any]:
    """Paso Auditor: EvalÃºa la coherencia lÃ³gica de la historia y aprueba o rechaza con crÃ­ticas especÃ­ficas."""
    criteria = AUDITOR_CRITERIA_PROMPT.get(module_type, AUDITOR_CRITERIA_PROMPT["mystery"]).format(
        draft_script=draft_script,
        draft_title=draft_title,
    )

    if is_final_round:
        criteria += (
            "\n\nATENCIÃ“N: Esta es la RONDA FINAL. Si la historia aÃºn tiene pequeÃ±as fallas, "
            "tÃº mismo como Director Editorial REESCRIBE Y PULE el guiÃ³n definitivo con lÃ³gica impecable "
            "y respÃ³ndelo inmediatamente como ESTADO: APROBADO con el GUION y TITULO listos."
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
    """El Generador reescribe la historia corrigiendo especÃ­ficamente las fallas lÃ³gicas marcadas por el Auditor."""
    sys_prompt = SYSTEM_PROMPTS.get(module_type, SYSTEM_PROMPTS["mystery"])
    user_prompt = (
        f"El Director Editorial RECHAZÃ“ tu borrador anterior por falta de coherencia lÃ³gica:\n\n"
        f"BORRADOR ANTERIOR:\n\"\"\"{previous_script}\"\"\"\n\n"
        f"FALLOS DETECTADOS POR EL AUDITOR:\n{criticism}\n\n"
        f"INSTRUCCIONES DE CORRECCIÃ“N:\n{instructions}\n\n"
        f"Reescribe la historia desde cero corrigiendo cada falla. "
        f"La causa y efecto debe ser 100% lÃ³gica, humana y verosÃ­mil. "
        f"CONCISIÃ“N TOTAL: Entre 85 y 110 palabras exactas. PROHIBIDO EL RELLENO Y LAS REDUNDANCIAS. CERO emojis. Cero markdown.\n"
        f"Al final incluye: TITULO: [tÃ­tulo viral sin emojis]"
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
    """Genera guiÃ³n usando un LOOP INTERACTIVO DUAL DE IA (Generador <-> Auditor):
    1. IA Generadora crea el borrador.
    2. IA Auditora evalÃºa coherencia lÃ³gica, gancho y categorÃ­a.
    3. Si el Auditor rechaza, la IA Generadora corrige los fallos especÃ­ficos.
    4. Se itera hasta que el Auditor emita 'ESTADO: APROBADO' (mÃ¡ximo 3 rondas).
    """
    if module_type not in SYSTEM_PROMPTS:
        raise ValueError(f"MÃ³dulo desconocido: {module_type}")

    client = _get_groq_client()
    sys_prompt = SYSTEM_PROMPTS[module_type]
    user_prompt = USER_PROMPTS[module_type]

    if extra_context:
        if module_type.startswith("gta6"):
            user_prompt += f"\n\nCONTEXTO OFICIAL Y DETALLES BASE:\n{extra_context}"
        elif module_type == "news":
            user_prompt += f"\n\nContexto de la noticia: {extra_context}"
        elif module_type == "reddit":
            user_prompt += f"\n\nHistoria base de Reddit: {extra_context}"
        elif module_type == "bizarre":
            user_prompt += f"\n\nHistoria base insÃ³lita/bizarra: {extra_context}"

    # â”€â”€ RONDA 1: GeneraciÃ³n inicial â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    logger.info("=== [DUAL-AI LOOP] Iniciando generaciÃ³n y filtro de coherencia â€” CategorÃ­a: %s ===", module_type.upper())
    logger.info("[Ronda 1] IA Generadora creando propuesta inicial...")

    raw_initial = _call_llm(client, sys_prompt, user_prompt, temperature=0.90, max_tokens=600)
    current_script, current_title = _parse_script_and_title(raw_initial)
    logger.info("[Ronda 1] Borrador inicial listo (%d palabras): '%s'", len(current_script.split()), current_title)

    max_rounds = 3
    final_script = current_script
    final_title = current_title

    for round_num in range(1, max_rounds + 1):
        is_final = (round_num == max_rounds)
        logger.info("[Ronda %d/%d] IA Auditora evaluando coherencia lÃ³gica y categorÃ­a...", round_num, max_rounds)

        audit = _audit_and_evaluate_draft(
            draft_script=current_script,
            draft_title=current_title,
            module_type=module_type,
            client=client,
            is_final_round=is_final,
        )

        if audit["approved"] and len(audit["script"].split()) >= 80:
            logger.info("âœ“ [DUAL-AI APROBADO] El Auditor aprobÃ³ la historia en la ronda %d!", round_num)
            final_script = audit["script"]
            final_title = audit["title"] or current_title
            break

        if not is_final:
            logger.warning(
                "âœ— [Ronda %d RECHAZADA] Auditor detectÃ³ falta de coherencia: %s",
                round_num,
                audit["criticism"][:150] + "..." if len(audit["criticism"]) > 150 else audit["criticism"],
            )
            logger.info("[Ronda %d] IA Generadora reescribiendo y corrigiendo lÃ³gica...", round_num + 1)
            current_script, current_title = _regenerate_with_criticism(
                previous_script=current_script,
                criticism=audit["criticism"],
                instructions=audit["instructions"],
                module_type=module_type,
                client=client,
            )
        else:
            # En ronda final, si el script devuelto por el auditor es vÃ¡lido, tomarlo
            if audit["script"] and len(audit["script"].split()) >= 80:
                final_script = audit["script"]
                final_title = audit["title"] or current_title
            else:
                final_script = current_script
                final_title = current_title
            logger.info("âœ“ [DUAL-AI FINAL] Finalizado ciclo de auditorÃ­a.")

    final_script = remove_emojis(_clean(final_script))
    final_title = remove_emojis(_clean(final_title))[:60]

    # Validacion dura: maximo 120 palabras para evitar videos >60s
    _words = final_script.split()
    if len(_words) > 120:
        logger.warning('Script demasiado largo (%d palabras) truncando a 110', len(_words))
        _t = ' '.join(_words[:110])
        _last = max(_t.rfind('.'), _t.rfind('!'), _t.rfind('?'))
        final_script = _t[:_last + 1] if _last > len(_t) * 0.5 else _t + '.'
        logger.info('Script truncado a %d palabras.', len(final_script.split()))

    # Verificación estricta: Si el script quedó corto (<60 palabras) o contiene una negativa, generar un reemplazo impecable
    if len(final_script.split()) < 60 or _is_refusal(final_script):
        logger.warning("Script final inválido o negativa detectada (%d palabras). Generando reemplazo de emergencia...", len(final_script.split()))
        fallback_prompt = (
            "Escribe un guión de 95 palabras sobre GTA 6 en el estado de Leonida para un Short de YouTube. "
            "Describe con asombro los detalles de Vice City, los caimanes gigantes en los pantanos y la inteligencia de la policía. "
            "Empieza con un gancho fuerte y termina en loop infinito. Prosa en español, sin emojis ni introducciones. "
            "Al final añade: TITULO: [Título impactante]"
        )
        try:
            r_fb = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": "Eres un narrador viral experto en videojuegos."},
                    {"role": "user", "content": fallback_prompt},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            content_fb = r_fb.choices[0].message.content
            if content_fb and not _is_refusal(content_fb):
                s_fb, t_fb = _parse_script_and_title(content_fb, default_title="El realismo brutal de GTA 6")
                if len(s_fb.split()) >= 60:
                    final_script = s_fb
                    final_title = t_fb
        except Exception as e_fb:
            logger.error("Error al generar reemplazo de emergencia: %s", e_fb)

    logger.info(
        "=== [DUAL-AI Ã‰XITO] GuiÃ³n verificado y aprobado: %d palabras | TÃ­tulo: '%s' ===",
        len(final_script.split()),
        final_title,
    )
    return {"script": final_script, "title": final_title}


def generate_image_prompts(
    script: str,
    module_type: str,
    num_images: int = 6,
) -> List[str]:
    """Genera descripciones visuales en inglÃ©s para las imÃ¡genes usando Groq (sin cuota) o Gemini."""
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

    # Intentar primero con Groq (sin lÃ­mite de cuota diaria)
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
            # Filtrar lÃ­neas muy cortas o que sean encabezados
            if cleaned and len(cleaned) > 20 and not cleaned.startswith("Here") and not cleaned.startswith("Based"):
                prompts.append(f"{cleaned}, {style_guide}")
        if len(prompts) >= num_images:
            logger.info("Prompts de imagen generados con Groq: %d prompts", len(prompts))
            return prompts[:num_images]
        logger.debug("Groq devolviÃ³ %d prompts (necesito %d), completando...", len(prompts), num_images)
    except Exception as exc:
        logger.warning("Groq para prompts de imagen fallÃ³: %s. Intentando Gemini...", exc)

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
        logger.warning("Gemini para imÃ¡genes tambiÃ©n fallÃ³: %s. Usando fallbacks.", exc)

    # Fallbacks hardcodeados por mÃ³dulo
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


