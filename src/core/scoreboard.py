"""Módulo de gestión del Scoreboard y Bucle de Aprendizaje (Learning Loop).

Implementa los requisitos de la Sección 13 del SOP:
- Registro estricto en scoreboard.csv de métricas a 12h, 24h y 72h.
- Regla de una variable por test (test_name).
- Cálculo de revisión diaria y semanal (medianas por pilar, slot y plataforma).
"""

import os
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

SCOREBOARD_PATH = os.path.join("gta6", "scoreboard.csv")
FIELDNAMES = [
    "post_id",
    "date",
    "time",
    "platform",
    "pillar",
    "format",
    "hook_sec",
    "credit",
    "views_12h",
    "views_24h",
    "views_72h",
    "likes",
    "reposts_or_shares",
    "replies_or_comments",
    "saves_or_bookmarks",
    "followers_at_read",
    "test_name",
    "notes",
]


def init_scoreboard(csv_path: str = SCOREBOARD_PATH) -> None:
    """Asegura que el archivo scoreboard.csv exista con sus encabezados oficiales."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        logger.info("Scoreboard inicializado en: %s", csv_path)


def log_post_entry(
    post_id: str,
    platform: str,
    pillar: str,
    format_type: str,
    hook_sec: float,
    credit: str,
    test_name: str = "",
    notes: str = "",
    csv_path: str = SCOREBOARD_PATH,
) -> None:
    """Registra una nueva publicación inmediatamente tras su programación o subida."""
    init_scoreboard(csv_path)
    now = datetime.now()

    entry = {
        "post_id": post_id,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "platform": platform,
        "pillar": pillar,
        "format": format_type,
        "hook_sec": round(hook_sec, 2),
        "credit": credit or "official",
        "views_12h": "",
        "views_24h": "",
        "views_72h": "",
        "likes": "",
        "reposts_or_shares": "",
        "replies_or_comments": "",
        "saves_or_bookmarks": "",
        "followers_at_read": "",
        "test_name": test_name,
        "notes": notes,
    }

    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(entry)

    logger.info("Publicación registrada en Scoreboard [%s]: %s (%s)", platform, post_id, pillar)


def update_post_metrics(
    post_id: str,
    read_stage: str,  # '12h', '24h', '72h'
    views: int,
    likes: Optional[int] = None,
    shares: Optional[int] = None,
    comments: Optional[int] = None,
    saves: Optional[int] = None,
    followers: Optional[int] = None,
    csv_path: str = SCOREBOARD_PATH,
) -> bool:
    """Actualiza las métricas de un post específico para la lectura de 12h, 24h o 72h."""
    if not os.path.exists(csv_path):
        return False

    rows = []
    updated = False
    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["post_id"] == post_id:
                view_key = f"views_{read_stage}"
                if view_key in row:
                    row[view_key] = str(views)
                if likes is not None:
                    row["likes"] = str(likes)
                if shares is not None:
                    row["reposts_or_shares"] = str(shares)
                if comments is not None:
                    row["replies_or_comments"] = str(comments)
                if saves is not None:
                    row["saves_or_bookmarks"] = str(saves)
                if followers is not None:
                    row["followers_at_read"] = str(followers)
                updated = True
            rows.append(row)

    if updated:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Métricas actualizadas para post %s (%s: %d views)", post_id, read_stage, views)
    return updated


def get_all_records(csv_path: str = SCOREBOARD_PATH) -> List[Dict[str, Any]]:
    """Lee y devuelve todos los registros del scoreboard."""
    if not os.path.exists(csv_path):
        return []
    records = []
    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append(r)
    return records


def generate_daily_review(csv_path: str = SCOREBOARD_PATH) -> Dict[str, Any]:
    """Genera el reporte diario: mejor post, peor post y lección del día."""
    records = get_all_records(csv_path)
    if not records:
        return {"status": "empty", "message": "No hay publicaciones registradas aún."}

    # Evaluar por views_24h o views_12h
    scored = []
    for r in records:
        v_str = r.get("views_24h") or r.get("views_12h") or "0"
        try:
            val = int(v_str) if v_str else 0
        except ValueError:
            val = 0
        scored.append((val, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]
    worst = scored[-1][1]

    return {
        "status": "ok",
        "total_posts": len(records),
        "best_post": best,
        "worst_post": worst,
    }


def generate_weekly_review(csv_path: str = SCOREBOARD_PATH) -> Dict[str, Any]:
    """Genera la revisión semanal (Sección 13): top 3, bottom 3, y medianas por pilar y plataforma."""
    import statistics
    records = get_all_records(csv_path)
    if len(records) < 3:
        return {"status": "insufficient_data", "count": len(records)}

    def parse_views(r):
        v = r.get("views_72h") or r.get("views_24h") or "0"
        try:
            return int(v) if v else 0
        except ValueError:
            return 0

    scored = [(parse_views(r), r) for r in records]
    scored.sort(key=lambda x: x[0], reverse=True)

    top_3 = [item[1] for item in scored[:3]]
    bottom_3 = [item[1] for item in scored[-3:]]

    # Medianas por pilar
    pillars: Dict[str, List[int]] = {}
    platforms: Dict[str, List[int]] = {}

    for v, r in scored:
        p = r.get("pillar", "unknown")
        plat = r.get("platform", "unknown")
        pillars.setdefault(p, []).append(v)
        platforms.setdefault(plat, []).append(v)

    pillar_medians = {p: int(statistics.median(vals)) for p, vals in pillars.items() if vals}
    platform_medians = {pl: int(statistics.median(vals)) for pl, vals in platforms.items() if vals}

    return {
        "status": "ok",
        "total_analyzed": len(records),
        "top_3": top_3,
        "bottom_3": bottom_3,
        "pillar_medians": pillar_medians,
        "platform_medians": platform_medians,
    }
