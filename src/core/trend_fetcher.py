"""Módulo de recolección de tendencias y memes en vivo de las últimas 24 horas.

Consulta feeds RSS de Reddit, Google News y Nitter para obtener los memes,
clips virales y novedades MÁS CONCRETAS del día sobre GTA 6.

Devuelve no solo el titular sino también:
 - La noticia exacta / meme / evento
 - Un keyword para buscar el clip de fondo relacionado
 - El tono (gracioso, impactante, polémico, etc.)
"""

import os
import json
import logging
import random
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# FEEDS RSS: Reddit (JSON), Google News
# ─────────────────────────────────────────────────────────────────────────────

REDDIT_FEEDS = [
    "https://www.reddit.com/r/GrandTheftAutoVI/top.json?t=day&limit=10",
    "https://www.reddit.com/r/GTA/top.json?t=day&limit=5",
]

GOOGLE_NEWS_FEEDS = [
    # Noticias y tendencias en español de las últimas 24 horas
    "https://news.google.com/rss/search?q=GTA+6+when:1d&hl=es-419&gl=CL&ceid=CL:es-419",
    # Noticias globales y descubrimientos en inglés de las últimas 24 horas
    "https://news.google.com/rss/search?q=GTA+6+when:1d&hl=en-US&gl=US&ceid=US:en",
    # Secretos, bugs, easter eggs y descubrimientos de jugadores en las últimas 24 horas
    "https://news.google.com/rss/search?q=GTA+6+(easter+egg+OR+secret+OR+discovery+OR+viral+OR+glitch)+when:1d&hl=en-US&gl=US&ceid=US:en",
    # Curiosidades y novedades en español
    "https://news.google.com/rss/search?q=GTA+6+(curiosidad+OR+secreto+OR+descubrimiento+OR+viral)+when:1d&hl=es-419&gl=CL&ceid=CL:es-419",
]

# ─────────────────────────────────────────────────────────────────────────────
# MAPEO: Keywords de noticia → query de clip de YouTube relacionado
# ─────────────────────────────────────────────────────────────────────────────

TOPIC_TO_CLIP_QUERY: List[Dict] = [
    {
        "keywords": ["cheat", "cheats", "truco", "trucos", "cheat code", "bloqueado", "blocked"],
        "clip_query": "GTA 6 cheats testing weapons chaos free roam -trailer -cutscene -live -livestream",
        "topic_tag": "cheats",
    },
    {
        "keywords": ["pc", "pc port", "pc version", "windows", "steam", "pc players", "computadora"],
        "clip_query": "GTA 6 console exclusive PS5 Xbox free roam gameplay -trailer -cutscene -live -livestream",
        "topic_tag": "pc_port",
    },
    {
        "keywords": ["npc", "npcs", "pedestrian", "peatón", "peatones", "crowd", "ai behavior"],
        "clip_query": "GTA 6 crazy npc moments open world funny pedestrians -trailer -cutscene -live -livestream",
        "topic_tag": "npcs",
    },
    {
        "keywords": ["alligator", "alligators", "caimán", "caiman", "swamp", "pantano", "water", "boat", "lancha"],
        "clip_query": "GTA 6 alligator attack swamp water gameplay -trailer -cutscene -live -livestream",
        "topic_tag": "alligator",
    },
    {
        "keywords": ["police", "cop", "cops", "5 star", "wanted", "chase", "pursuit", "policía", "persecución"],
        "clip_query": "GTA 6 police chase 5 stars escape wanted gameplay -trailer -cutscene -live -livestream",
        "topic_tag": "police",
    },
    {
        "keywords": ["realistic", "real life", "miami", "florida", "photo", "graphics", "4k", "real world", "gráfico"],
        "clip_query": "GTA 6 realistic graphics 4k free roam driving -trailer -cutscene -live -livestream",
        "topic_tag": "realism",
    },
    {
        "keywords": ["streamer", "twitch", "live", "reaction", "reacción", "stream", "youtuber", "content creator"],
        "clip_query": "GTA 6 streamer funny reaction moments gameplay -trailer -cutscene -live -livestream",
        "topic_tag": "streamer",
    },
    {
        "keywords": ["meme", "memes", "funny", "humor", "gracioso", "viral", "lol", "hilarious", "absurd", "wtf"],
        "clip_query": "GTA 6 funny moments viral clips open world -trailer -cutscene -live -livestream",
        "topic_tag": "memes",
    },
    {
        "keywords": ["driving", "car", "cars", "race", "speed", "auto", "autos", "supercar", "drift"],
        "clip_query": "GTA 6 PS5 supercar driving night speed -trailer -cutscene -live -livestream",
        "topic_tag": "driving",
    },
    {
        "keywords": ["lucia", "jason", "protagonist", "protagonista", "character", "personaje"],
        "clip_query": "GTA 6 Lucia Jason gameplay open world free roam -trailer -cutscene -live -livestream",
        "topic_tag": "characters",
    },
    {
        "keywords": ["vice city", "leonida", "city", "ciudad", "map", "mapa", "open world", "environment"],
        "clip_query": "GTA 6 open world exploration 4k free roam -trailer -cutscene -live -livestream",
        "topic_tag": "world",
    },
    {
        "keywords": ["release", "launch", "date", "hype", "pre-order", "lanzamiento", "fecha"],
        "clip_query": "GTA 6 PS5 official gameplay open world exploration -trailer -cutscene -live -livestream",
        "topic_tag": "launch",
    },
]

DEFAULT_CLIP_QUERIES = [
    "GTA 6 PS5 4K HDR Gameplay -trailer -cutscene -live -livestream",
    "Grand Theft Auto VI Gameplay -trailer -cutscene -live -livestream",
    "GTA 6 Lucia Jason gameplay open world -trailer -cutscene -live -livestream",
    "GTA 6 PS5 police chase 5 stars gameplay -trailer -cutscene -live -livestream",
]

# Fallbacks si no hay internet / Reddit está caído
FALLBACK_TOPICS = [
    {
        "title": "Rockstar bloqueó los trucos clásicos en GTA 6 hasta terminar el juego",
        "source": "Fallback",
        "detail": "La comunidad de GTA 6 está enloquecida: Rockstar bloqueó todos los cheats hasta que termines la historia principal.",
        "clip_query": "GTA 6 cheats testing funny weapons chaos free roam -trailer -cutscene -live -livestream",
        "topic_tag": "cheats",
        "score": 0,
    },
    {
        "title": "Los NPCs de GTA 6 están haciendo cosas absurdas y nadie sabe por qué",
        "source": "Fallback",
        "detail": "El nuevo sistema de IA de los NPCs tiene comportamientos completamente impredecibles que se hacen virales.",
        "clip_query": "GTA 6 crazy npc moments open world funny -trailer -cutscene -live -livestream",
        "topic_tag": "npcs",
        "score": 0,
    },
    {
        "title": "GTA 6 confundido con videos reales de Miami en redes sociales",
        "source": "Fallback",
        "detail": "Los gráficos fotorrealistas de GTA 6 están confundiendo a la gente en Twitter y TikTok.",
        "clip_query": "GTA 6 realistic graphics Vice City 4k free roam driving -trailer -cutscene -live -livestream",
        "topic_tag": "realism",
        "score": 0,
    },
    {
        "title": "Un caimán destruyó la lancha de un jugador en GTA 6 y el clip es viral",
        "source": "Fallback",
        "detail": "Un clip de un caimán atacando una lancha en los pantanos de Leonida se volvió viral en Reddit.",
        "clip_query": "GTA 6 alligator attack swamp water gameplay -trailer -cutscene -live -livestream",
        "topic_tag": "alligator",
        "score": 0,
    },
    {
        "title": "Streamer pierde 5 estrellas de forma ridícula en GTA 6 y el clip explota en TikTok",
        "source": "Fallback",
        "detail": "Un momento de un streamer huyendo de la policía de forma completamente caótica se hizo viral.",
        "clip_query": "GTA 6 police chase 5 stars escape funny streamer -trailer -cutscene -live -livestream",
        "topic_tag": "police",
        "score": 0,
    },
]


def _make_request(url: str, timeout: int = 10) -> Optional[bytes]:
    """Hace una petición HTTP con headers de navegador real."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as exc:
        logger.debug("Error en request a %s: %s", url[:60], exc)
        return None


def _fetch_reddit_topics() -> List[Dict]:
    """Obtiene los posts más virales del día de Reddit sobre GTA 6."""
    topics = []
    for feed_url in REDDIT_FEEDS:
        data = _make_request(feed_url)
        if not data:
            continue
        try:
            parsed = json.loads(data)
            children = parsed.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                title = post.get("title", "").strip()
                score = post.get("score", 0)
                selftext = post.get("selftext", "")[:300]

                if not title or score < 30:
                    continue

                # Solo posts relacionados con GTA 6
                gta_keywords = ["gta 6", "gta6", "grand theft auto", "rockstar", "lucia", "vice city", "leonida", "gta vi"]
                if not any(k in title.lower() for k in gta_keywords):
                    continue

                # Extraer video_url si el post incluye o enlaza un clip viral directo
                video_url = ""
                post_url = post.get("url", "")
                permalink = post.get("permalink", "")
                if post.get("is_video") and permalink:
                    video_url = f"https://www.reddit.com{permalink}"
                elif any(dom in post_url.lower() for dom in ["v.redd.it", "youtube.com/watch", "youtu.be", "twitter.com", "x.com", "tiktok.com", "clips.twitch.tv"]):
                    video_url = post_url

                # Enriquecer con clip query contextual
                combined = f"{title} {selftext}"
                clip_info = _get_clip_query_for_topic(combined)

                topics.append({
                    "title": title,
                    "source": "Reddit",
                    "score": score,
                    "detail": selftext if selftext and selftext not in ("[deleted]", "[removed]") else "",
                    "video_url": video_url,
                    "published": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "clip_query": clip_info["clip_query"],
                    "topic_tag": clip_info["topic_tag"],
                })

        except Exception as exc:
            logger.warning("Error parseando Reddit JSON: %s", exc)

    topics.sort(key=lambda x: x.get("score", 0), reverse=True)
    return topics[:6]


def _fetch_google_news_topics() -> List[Dict]:
    """Obtiene noticias/memes de GTA 6 desde Google News RSS."""
    topics = []
    for feed_url in GOOGLE_NEWS_FEEDS:
        data = _make_request(feed_url)
        if not data:
            continue
        try:
            root = ET.fromstring(data)
            items = root.findall(".//item")
            for it in items:
                title_elem = it.find("title")
                pub_elem = it.find("pubDate")
                desc_elem = it.find("description")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                pub = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

                if not title:
                    continue
                if any(t["title"] == title for t in topics):
                    continue

                combined = f"{title} {desc}"
                clip_info = _get_clip_query_for_topic(combined)

                topics.append({
                    "title": title,
                    "source": "Google News",
                    "score": 100,
                    "detail": desc[:200],
                    "published": pub,
                    "clip_query": clip_info["clip_query"],
                    "topic_tag": clip_info["topic_tag"],
                })

                if len(topics) >= 8:
                    break
        except Exception as exc:
            logger.warning("Error parseando Google News RSS: %s", exc)

    return topics


def _get_clip_query_for_topic(topic_text: str) -> Dict:
    """Dada la noticia/meme del día, devuelve la query de clip más relacionada."""
    text_lower = topic_text.lower()
    for mapping in TOPIC_TO_CLIP_QUERY:
        if any(kw in text_lower for kw in mapping["keywords"]):
            return {
                "clip_query": mapping["clip_query"],
                "topic_tag": mapping["topic_tag"],
            }
    return {
        "clip_query": random.choice(DEFAULT_CLIP_QUERIES),
        "topic_tag": "general",
    }


def fetch_live_trending_topics(max_topics: int = 8) -> List[Dict]:
    """Obtiene los temas más calientes de GTA 6 en las últimas 24 horas.

    Cada topic incluye:
      - title: titular de la noticia/meme
      - source: Reddit / Google News
      - score: popularidad
      - detail: descripción extra
      - published: fecha
      - clip_query: query de YouTube para buscar el clip relacionado
      - topic_tag: tag corto del tema
    """
    all_topics = []

    logger.info("Consultando Google News por tendencias y noticias GTA 6 de las últimas 24h...")
    news_topics = _fetch_google_news_topics()
    all_topics.extend(news_topics)
    logger.info("Google News: %d noticias y tendencias encontradas", len(news_topics))

    if len(all_topics) < 4:
        logger.info("Consultando Reddit por tendencias GTA 6 de las últimas 24h...")
        reddit_topics = _fetch_reddit_topics()
        all_topics.extend(reddit_topics)
        logger.info("Reddit: %d posts virales encontrados", len(reddit_topics))

    # Deduplicar
    seen = set()
    unique = []
    for t in all_topics:
        key = t["title"][:60]
        if key not in seen:
            seen.add(key)
            unique.append(t)
        if len(unique) >= max_topics:
            break

    if not unique:
        logger.warning("No se encontraron tendencias en vivo. Usando fallbacks.")
        unique = FALLBACK_TOPICS[:max_topics]

    logger.info("✓ %d tendencias y memes en vivo recolectados para hoy.", len(unique))
    return unique


USED_TRENDS_FILE = os.path.join("gta6", "media", "used_trends.json")


def load_used_trends() -> List[str]:
    """Carga los títulos de tendencias ya usados para no repetir el mismo tema."""
    if os.path.exists(USED_TRENDS_FILE):
        try:
            with open(USED_TRENDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def mark_trend_as_used(title: str) -> None:
    """Registra una tendencia como usada."""
    used = load_used_trends()
    clean_t = title.strip()[:60]
    if clean_t and clean_t not in used:
        used.append(clean_t)
    if len(used) > 40:
        used = used[-40:]
    try:
        os.makedirs(os.path.dirname(USED_TRENDS_FILE), exist_ok=True)
        with open(USED_TRENDS_FILE, "w", encoding="utf-8") as f:
            json.dump(used, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_top_trending_topic(prefer_fresh: bool = True) -> Dict:
    """Devuelve un tema viral del momento con su clip_query asociada.

    Si prefer_fresh=True, rota entre los temas disponibles evitando repetir
    los que ya se usaron en las últimas publicaciones.
    """
    topics = fetch_live_trending_topics(max_topics=10)
    if not topics:
        return random.choice(FALLBACK_TOPICS)

    if prefer_fresh:
        used = load_used_trends()
        unused = [t for t in topics if t.get("title", "")[:60] not in used]
        if unused:
            chosen = unused[0]
            mark_trend_as_used(chosen["title"])
            return chosen

    chosen = topics[0]
    mark_trend_as_used(chosen.get("title", ""))
    return chosen


def get_live_context_for_prompt(selected_topic: Optional[Dict] = None) -> str:
    """Genera el bloque de contexto para inyectar en el prompt de la IA."""
    topics = fetch_live_trending_topics(max_topics=6)
    if not topics:
        return ""

    target_title = selected_topic.get("title", "") if selected_topic else topics[0]["title"]
    target_detail = selected_topic.get("detail", "") if selected_topic else topics[0].get("detail", "")

    lines = [
        "═══════════════════════════════════════════════════",
        "NOTICIA O TENDENCIA OBLIGATORIA A COMENTAR HOY:",
        f"TITULAR: {target_title}",
    ]
    if target_detail:
        lines.append(f"DETALLES CLAVE: {target_detail}")
    lines.extend([
        "═══════════════════════════════════════════════════",
        "OTRAS TENDENCIAS DE HOY (CONTEXTO ADICIONAL):",
    ])
    for i, t in enumerate(topics[:5], 1):
        source_label = f"[{t.get('source', 'Web')}]"
        lines.append(f"{i}. {source_label} {t['title']}")

    lines.extend([
        "═══════════════════════════════════════════════════",
        "INSTRUCCIÓN SAGRADA: Tu guión DEBE tratar exclusivamente sobre el TITULAR principal de arriba.",
        "Cero menciones a parches viejos (1.02, etc.), ni tráilers antiguos. Todo enfocado en la noticia fresca de hoy.",
        "═══════════════════════════════════════════════════",
    ])

    return "\n".join(lines)


def save_facts_update(topics: List[Dict], facts_path: str = "gta6/facts.md") -> None:
    """Actualiza automáticamente facts.md con las últimas noticias del día."""
    if not topics:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    date_header = f"## Tendencias Virales — {today}"

    try:
        import os
        os.makedirs(os.path.dirname(facts_path), exist_ok=True)

        existing = ""
        if os.path.exists(facts_path):
            with open(facts_path, "r", encoding="utf-8-sig") as f:
                existing = f.read()

        section = f"\n\n{date_header}\n"
        for t in topics[:5]:
            section += f"- [{t.get('source', 'Web')}] {t['title']}"
            if t.get("detail"):
                section += f" — {t['detail'][:100]}"
            section += "\n"

        if date_header in existing:
            # Reemplazar la sección de hoy con las tendencias más recientes
            parts = existing.split(date_header)
            # Conservar lo anterior y reescribir la sección de hoy
            next_header_idx = parts[1].find("\n## ")
            after = parts[1][next_header_idx:] if next_header_idx != -1 else ""
            updated = parts[0].rstrip() + section.rstrip() + after
            with open(facts_path, "w", encoding="utf-8") as f:
                f.write(updated)
            logger.info("✓ facts.md refrescado con las últimas tendencias de hoy.")
            return

        with open(facts_path, "a", encoding="utf-8") as f:
            f.write(section)
        logger.info("✓ facts.md actualizado con %d tendencias de hoy.", len(topics[:5]))
    except Exception as exc:
        logger.warning("No se pudo actualizar facts.md: %s", exc)
    except Exception as exc:
        logger.warning("No se pudo actualizar facts.md: %s", exc)
