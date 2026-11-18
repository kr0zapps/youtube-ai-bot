"""Planificador automático de GTA 6 Clipping Page + módulos legacy.

Horario diario según el SOP (Sección 9 / config.yaml):
  Pilar GTA6 News  — 08:00, 14:00, 20:00
  Pilar GTA6 Tips  — 10:00, 17:00
  Pilar GTA6 Clip  — 12:00, 21:00

Los módulos mystery/news/reddit se mantienen como jobs opcionales
si el canal es mixto. Coméntalos en config.yaml para desactivarlos.

Uso:
    python scheduler.py                     # Arranca en modo producción
    python scheduler.py --dry-run           # Genera videos sin subir
    python scheduler.py --no-upload         # Genera videos sin subir
    python scheduler.py --only-gta6         # Solo los 3 pilares de GTA 6
"""

import os
import sys
import yaml
import signal
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("scheduler")


def setup_logging(log_file: str = "logs/bot.log") -> None:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [SCHEDULER] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def execute_gta6_job(pillar: str, config: Dict[str, Any], dry_run: bool, no_upload: bool) -> None:
    """Ejecuta el pipeline de GTA 6 para un pilar específico."""
    logger.info("=" * 54)
    logger.info("GTA 6 JOB DISPARADO — Pilar: %s", pillar.upper())
    logger.info("=" * 54)
    from src.modules import gta6
    try:
        start = datetime.now()
        video_path = gta6.run(pillar=pillar, config=config, dry_run=dry_run, no_upload=no_upload)
        elapsed = (datetime.now() - start).total_seconds()
        logger.info("GTA 6 [%s] completado en %.1fs. Video: %s", pillar.upper(), elapsed, video_path)
    except Exception as exc:
        logger.error("Error en GTA 6 [%s]: %s", pillar.upper(), exc, exc_info=True)


def execute_legacy_job(module_name: str, config: Dict[str, Any], dry_run: bool, no_upload: bool) -> None:
    """Ejecuta un módulo legacy (mystery, news, reddit, bizarre)."""
    logger.info("=" * 54)
    logger.info("LEGACY JOB DISPARADO — Módulo: %s", module_name.upper())
    logger.info("=" * 54)
    from src.modules import mystery, news, reddit, bizarre
    runners = {"mystery": mystery.run, "news": news.run, "reddit": reddit.run, "bizarre": bizarre.run}
    runner = runners.get(module_name)
    if not runner:
        logger.error("Módulo desconocido: %s", module_name)
        return
    try:
        start = datetime.now()
        video_path = runner(config=config, dry_run=dry_run, no_upload=no_upload)
        elapsed = (datetime.now() - start).total_seconds()
        logger.info("[%s] completado en %.1fs. Video: %s", module_name.upper(), elapsed, video_path)
    except Exception as exc:
        logger.error("Error en módulo [%s]: %s", module_name.upper(), exc, exc_info=True)


def parse_time(time_str: str) -> Tuple[int, int]:
    h, m = time_str.strip().split(":")
    return int(h), int(m)


def start_scheduler(
    config_path: str = "config.yaml",
    dry_run: bool = False,
    no_upload: bool = False,
    only_gta6: bool = False,
) -> None:
    config = load_config(config_path)
    sched_cfg = config.get("schedule", {})
    timezone_str = sched_cfg.get("timezone", "America/Santiago")

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler no encontrado. Ejecuta: pip install -r requirements.txt")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=timezone_str)
    summary: List[str] = []

    # ── Pilares GTA 6 ────────────────────────────────────────────────
    gta6_jobs: List[Tuple[str, List[str]]] = [
        ("news", sched_cfg.get("gta6_news_times", ["08:00", "14:00", "20:00"])),
        ("tips", sched_cfg.get("gta6_tips_times", ["10:00", "17:00"])),
        ("clip", sched_cfg.get("gta6_clip_times", ["12:00", "21:00"])),
    ]

    for pillar, times in gta6_jobs:
        for t in times:
            h, m = parse_time(t)
            jid = f"gta6_{pillar}_{h:02d}{m:02d}"
            scheduler.add_job(
                execute_gta6_job,
                trigger=CronTrigger(hour=h, minute=m, timezone=timezone_str),
                id=jid,
                name=f"GTA6 {pillar.upper()} {t}",
                args=[pillar, config, dry_run, no_upload],
                replace_existing=True,
            )
            summary.append(f"  GTA6 [{pillar.upper():<4}] — {t} ({timezone_str})")

    # ── Módulos legacy (omitir si --only-gta6) ───────────────────────
    if not only_gta6:
        legacy_jobs: List[Tuple[str, List[str]]] = [
            ("mystery", sched_cfg.get("mystery_times", ["09:00", "15:00", "21:00"])),
            ("news",    sched_cfg.get("news_times",    ["08:00", "14:00", "20:00"])),
            ("reddit",  sched_cfg.get("reddit_times",  ["10:00", "16:00", "22:00"])),
        ]
        for module_name, times in legacy_jobs:
            for t in times:
                h, m = parse_time(t)
                jid = f"legacy_{module_name}_{h:02d}{m:02d}"
                scheduler.add_job(
                    execute_legacy_job,
                    trigger=CronTrigger(hour=h, minute=m, timezone=timezone_str),
                    id=jid,
                    name=f"{module_name.capitalize()} {t}",
                    args=[module_name, config, dry_run, no_upload],
                    replace_existing=True,
                )
                summary.append(f"  Legacy[{module_name.upper():<7}] — {t} ({timezone_str})")

    logger.info("=" * 54)
    logger.info("   GTA 6 CLIPPING PAGE — SCHEDULER ACTIVO")
    logger.info("=" * 54)
    logger.info("Zona horaria : %s", timezone_str)
    logger.info("dry-run      : %s | no-upload: %s", dry_run, no_upload)
    logger.info("Solo GTA 6   : %s", only_gta6)
    logger.info("Jobs registrados (%d):", len(summary))
    for line in sorted(summary):
        logger.info(line)
    logger.info("=" * 54)
    logger.info("Scheduler en ejecución. Ctrl+C para detener.")

    def _shutdown(sig, frame):
        logger.info("Señal de interrupción. Deteniendo scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GTA 6 Clipping Page Scheduler",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config",      default="config.yaml")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--no-upload",   action="store_true")
    parser.add_argument(
        "--only-gta6",
        action="store_true",
        help="Desactiva los módulos legacy y ejecuta solo los 3 pilares de GTA 6.",
    )
    args = parser.parse_args()
    setup_logging()
    start_scheduler(
        config_path=args.config,
        dry_run=args.dry_run,
        no_upload=args.no_upload,
        only_gta6=args.only_gta6,
    )
