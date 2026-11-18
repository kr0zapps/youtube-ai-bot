"""Script de Día de Lanzamiento — GTA 6.

Ejecuta el plan de la Sección 10 del SOP de forma completamente automática:
1. Descarga clips de GTA 6 de YouTube (streams y videos más recientes).
2. Convierte todos los clips a formato vertical 1080x1920.
3. Genera y publica videos en los 3 pilares en modo rafaga (cada 1-2 horas).
4. Registra todo en scoreboard.csv y log.md.

Uso:
    python launch_day.py                    # Producción completa
    python launch_day.py --dry-run          # Sin subir a plataformas
    python launch_day.py --skip-download    # Usar clips ya descargados
    python launch_day.py --pillar news      # Solo un pilar específico
"""

import os
import sys
import time
import logging
import argparse

# Fix encoding Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/launch_day.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("launch_day")


def run_launch_day(
    dry_run: bool = False,
    skip_download: bool = False,
    pillar: str = "all",
    delay_between_posts: int = 90,
) -> None:
    """Ejecuta el plan completo de día de lanzamiento del SOP Sección 10."""
    import yaml
    from src.core.clip_downloader import run_launch_day_download
    from src.modules import gta6

    os.makedirs("logs", exist_ok=True)

    logger.info("=" * 60)
    logger.info("   GTA 6 LAUNCH DAY — MODO AUTOMATICO ACTIVADO")
    logger.info("   Fecha: %s", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # Cargar config
    config = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # ── Paso 1: Descargar clips ─────────────────────────────────────
    if not skip_download:
        logger.info("[PASO 1] Descargando clips de GTA 6 de YouTube...")
        clips = run_launch_day_download(
            num_queries=3,
            clip_start_sec=45,
            clip_duration_sec=55,
        )
        if clips:
            logger.info("[PASO 1] ✓ %d clips descargados y convertidos a vertical.", len(clips))
        else:
            logger.warning("[PASO 1] No se descargaron clips. Se usará el fondo de respaldo (GTA 5).")
    else:
        logger.info("[PASO 1] --skip-download activado. Usando clips existentes en gta6/media/")

    # ── Paso 2: Rafaga de publicaciones ────────────────────────────
    # Según el SOP Sección 10: post cada 1-2h durante las primeras 48h
    pillars = ["news", "tips", "clip"] if pillar == "all" else [pillar]

    logger.info("[PASO 2] Iniciando ráfaga de publicaciones — Pilares: %s", pillars)
    logger.info("         Delay entre posts: %ds", delay_between_posts)

    total_published = 0
    for idx, p in enumerate(pillars):
        logger.info("-" * 50)
        logger.info("Generando post #%d — Pilar: %s", idx + 1, p.upper())
        try:
            video_path = gta6.run(
                pillar=p,
                config=config,
                dry_run=dry_run,
                no_upload=False,
                test_name=f"LaunchDay_{p}",
            )
            logger.info("✓ Post publicado: %s", video_path)
            total_published += 1
        except Exception as exc:
            logger.error("✗ Error en pilar '%s': %s", p, exc, exc_info=True)

        # Pausa entre posts (excepto el último)
        if idx < len(pillars) - 1:
            logger.info("Esperando %ds antes del siguiente post...", delay_between_posts)
            time.sleep(delay_between_posts)

    logger.info("=" * 60)
    logger.info("LANZAMIENTO COMPLETADO")
    logger.info("Posts publicados: %d / %d", total_published, len(pillars))
    logger.info("Revisa tus canales y actualiza scoreboard.csv en 12h.")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GTA 6 Launch Day Automation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Genera videos sin subir.")
    parser.add_argument("--skip-download", action="store_true", help="Salta la descarga de clips.")
    parser.add_argument(
        "--pillar",
        choices=["news", "tips", "clip", "all"],
        default="all",
        help="Pilar específico a publicar o 'all' para los 3.",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=90,
        help="Segundos de espera entre posts (default: 90s).",
    )
    args = parser.parse_args()
    run_launch_day(
        dry_run=args.dry_run,
        skip_download=args.skip_download,
        pillar=args.pillar,
        delay_between_posts=args.delay,
    )
