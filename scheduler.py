"""Planificador y temporizador automático de tareas (Cron/Scheduler).

Utiliza APScheduler para ejecutar los módulos de generación y publicación
de YouTube Shorts en los horarios configurados en config.yaml.
"""

import os
import sys
import yaml
import signal
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("scheduler")


def setup_logging(log_file: str = "logs/bot.log") -> None:
    """Configura logging para el planificador."""
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
    """Carga configuración de config.yaml."""
    if not os.path.exists(config_path):
        logger.warning("No se encontró %s. Usando configuración predeterminada.", config_path)
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def execute_job(module_name: str, config: Dict[str, Any], dry_run: bool, no_upload: bool) -> None:
    """Función objetivo ejecutada en cada disparo programado."""
    logger.info("==================================================")
    logger.info("⏰ DISPARO PROGRAMADO: MÓDULO '%s'", module_name.upper())
    logger.info("==================================================")

    from src.modules import mystery, news, reddit

    runners = {
        "mystery": mystery.run,
        "news": news.run,
        "reddit": reddit.run,
    }

    runner = runners.get(module_name)
    if not runner:
        logger.error("Módulo desconocido para el job: %s", module_name)
        return

    try:
        start_time = datetime.now()
        video_path = runner(config=config, dry_run=dry_run, no_upload=no_upload)
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "✅ Job '%s' completado con éxito en %.1f segundos. Archivo: %s",
            module_name,
            duration,
            video_path,
        )
    except Exception as exc:
        logger.error("❌ Fallo en la ejecución programada de '%s': %s", module_name, exc, exc_info=True)


def parse_time_str(time_str: str) -> tuple[int, int]:
    """Convierte un string 'HH:MM' en tupla de enteros (hora, minuto)."""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])


def start_scheduler(
    config_path: str = "config.yaml",
    dry_run: bool = False,
    no_upload: bool = False,
) -> None:
    """Inicia el planificador bloqueante con los horarios definidos en config.yaml."""
    config = load_config(config_path)
    schedule_cfg = config.get("schedule", {})
    timezone_str = schedule_cfg.get("timezone", "America/Santiago")

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error(
            "El paquete APScheduler no está instalado. Ejecuta: pip install -r requirements.txt"
        )
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=timezone_str)

    # Mapeo de módulos y sus listas de horarios
    schedule_mapping = [
        ("mystery", schedule_cfg.get("mystery_times", ["09:00", "15:00", "21:00"])),
        ("news", schedule_cfg.get("news_times", ["08:00", "14:00", "20:00"])),
        ("reddit", schedule_cfg.get("reddit_times", ["10:00", "16:00", "22:00"])),
    ]

    total_jobs = 0
    registered_jobs_summary: List[str] = []

    for module_name, times_list in schedule_mapping:
        for t_str in times_list:
            try:
                hour, minute = parse_time_str(t_str)
                job_id = f"{module_name}_{hour:02d}{minute:02d}"
                trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone_str)

                scheduler.add_job(
                    execute_job,
                    trigger=trigger,
                    id=job_id,
                    name=f"Subida {module_name.capitalize()} a las {t_str}",
                    args=[module_name, config, dry_run, no_upload],
                    replace_existing=True,
                )
                registered_jobs_summary.append(f"  • [{module_name.upper():<7}] {t_str} ({timezone_str})")
                total_jobs += 1
            except Exception as exc:
                logger.error("Error al programar horario '%s' para '%s': %s", t_str, module_name, exc)

    logger.info("==================================================")
    logger.info("   🤖 YOUTUBE AI BOT — PLANIFICADOR AUTOMÁTICO   ")
    logger.info("==================================================")
    logger.info("Zona Horaria: %s", timezone_str)
    logger.info("Modo Dry-Run: %s | Modo No-Upload: %s", dry_run, no_upload)
    logger.info("Total de tareas programadas: %d", total_jobs)
    logger.info("Cronograma diario activo:")
    for summary_line in registered_jobs_summary:
        logger.info(summary_line)
    logger.info("==================================================")
    logger.info("Scheduler en ejecución. Presione Ctrl+C para detener.")

    # Manejar señales de terminación
    def handle_sigint(sig, frame):
        logger.info("Señal de interrupción recibida. Deteniendo scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler finalizado por el usuario.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YouTube AI Bot Scheduler — Programa subidas automáticas",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Ruta al archivo config.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecuta las tareas sin subir a YouTube y mantiene temporales.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Ejecuta las tareas y ensambla los videos sin subir a YouTube.",
    )
    args = parser.parse_args()

    setup_logging()
    start_scheduler(
        config_path=args.config,
        dry_run=args.dry_run,
        no_upload=args.no_upload,
    )
