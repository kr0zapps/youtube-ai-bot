"""Módulo de recolección de tendencias y memes en vivo de las últimas 24 horas.

Consulta feeds RSS de noticias virales, Reddit y tendencias de Google News
para inyectar los temas más calientes del día en el prompt del generador de guiones.
"""

import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    # Noticias virales y memes en inglés (Reddit, clips, streamers)
    "https://news.google.com/rss/search?q=GTA+6+(viral+OR+meme+OR+reddit+OR+clips)+when:1d&hl=en-US&gl=US&ceid=US:en",
    # Noticias y tendencias en español de las últimas 24 horas
    "https://news.google.com/rss/search?q=GTA+6+when:1d&hl=es-419&gl=CL&ceid=CL:es-419",
]


def fetch_live_trending_topics(max_topics: int = 8) -> List[Dict[str, str]]:
    """Obtiene los temas, memes y noticias más calientes de GTA 6 en las últimas 24 horas."""
    topics: List[Dict[str, str]] = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for feed_url in RSS_FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                items = root.findall(".//item")
                for it in items:
                    title_elem = it.find("title")
                    pub_elem = it.find("pubDate")
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    pub = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""
                    
                    # Filtrar temas irrelevantes o repetidos
                    if title and not any(t["title"] == title for t in topics):
                        topics.append({"title": title, "published": pub})
                    
                    if len(topics) >= max_topics:
                        break
        except Exception as e:
            logger.warning("Aviso al consultar feed de tendencias en vivo: %s", e)

        if len(topics) >= max_topics:
            break

    logger.info("✓ %d tendencias y memes en vivo recolectados para hoy.", len(topics))
    return topics


def get_live_context_for_prompt() -> str:
    """Genera un bloque de texto formateado con las tendencias en vivo de las últimas 24 horas."""
    topics = fetch_live_trending_topics(max_topics=6)
    if not topics:
        return ""

    lines = ["TENDENCIAS Y MEMES EN VIVO DE INTERNET (ÚLTIMAS 24 HORAS):"]
    for i, t in enumerate(topics, 1):
        lines.append(f"{i}. {t['title']}")

    return "\n".join(lines)
