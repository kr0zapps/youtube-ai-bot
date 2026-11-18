"""Entry point principal de YouTube AI Bot y GTA 6 Clipping Page Automation.

Permite ejecutar bajo demanda cualquier módulo del pipeline de generación de Shorts:
- gta6: Módulo oficial del SOP de GTA 6 (pilares: news, tips, clip)
- mystery: Historias de terror y misterio
- news: Noticias y curiosidades virales
- reddit: Reddit Stories en primera persona
- bizarre: Anécdotas bizarras y karma
- all: Ejecuta los módulos en secuencia

Uso:
    python main.py --module gta6 --pillar news
    python main.py --module gta6 --pillar tips --dry-run
    python main.py --module gta6 --pillar clip --test-name "Hook interrogativo"
    python main.py --review daily
    python main.py --review weekly
"""

import os
import sys
import yaml
import logging
import argparse

# Fix encoding para consola Windows (soporta emojis en logs)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime
from typing import Dict, Any

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def setup_logging(log_file: str = "logs/bot.log", level: int = logging.INFO) -> None:
    """Configura el sistema de logging para consola y archivo."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configurar root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def load_global_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Carga y valida el archivo de configuración global config.yaml."""
    if not os.path.exists(config_path):
        logging.warning("No se encontró %s. Se usarán valores predeterminados.", config_path)
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return cfg or {}
    except Exception as exc:
        logging.error("Error al leer %s: %s", config_path, exc)
        return {}


def run_pipeline(
    module_name: str,
    config: Dict[str, Any],
    dry_run: bool,
    no_upload: bool,
    pillar: str = "news",
    test_name: str = "",
    clip_url: str = None,
) -> bool:
    """Ejecuta un módulo específico y retorna True si tuvo éxito."""
    from src.modules import mystery, news, reddit, bizarre, gta6

    if module_name == "gta6":
        logging.info(">>> Iniciando ejecución del módulo GTA 6 [Pilar: %s] <<<", pillar.upper())
        start_time = datetime.now()
        try:
            video_path = gta6.run(
                pillar=pillar,
                config=config,
                dry_run=dry_run,
                no_upload=no_upload,
                test_name=test_name,
                clip_url=clip_url,
            )
            elapsed = (datetime.now() - start_time).total_seconds()
            logging.info(">>> Módulo GTA 6 completado en %.1fs. Video: %s <<<", elapsed, video_path)
            return True
        except Exception as exc:
            logging.error(">>> Error crítico al ejecutar GTA 6: %s <<<", exc, exc_info=True)
            return False

    modules_map = {
        "mystery": mystery.run,
        "reddit": reddit.run,
        "bizarre": bizarre.run,
        "news": news.run,
    }

    if module_name not in modules_map:
        logging.error("Módulo desconocido: '%s'. Opciones válidas: %s", module_name, list(modules_map.keys()) + ["gta6"])
        return False

    logging.info(">>> Iniciando ejecución del módulo: '%s' <<<", module_name.upper())
    start_time = datetime.now()

    try:
        video_path = modules_map[module_name](
            config=config,
            dry_run=dry_run,
            no_upload=no_upload,
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        logging.info(">>> Módulo '%s' completado en %.1fs. Video: %s <<<", module_name, elapsed, video_path)
        return True
    except Exception as exc:
        logging.error(">>> Error crítico al ejecutar el módulo '%s': %s <<<", module_name, exc, exc_info=True)
        return False


def handle_review(review_type: str) -> None:
    """Ejecuta las revisiones analíticas del Learning Loop (Sección 13)."""
    from src.core import scoreboard
    if review_type == "daily":
        logging.info("=== REVISIÓN DIARIA DE MÉTRICAS (Sección 13.4) ===")
        res = scoreboard.generate_daily_review()
        if res.get("status") == "ok":
            logging.info("Total publicaciones: %d", res['total_posts'])
            logging.info("Mejor post: %s | Gancho: %s s", res['best_post'].get('post_id'), res['best_post'].get('hook_sec'))
            logging.info("Peor post: %s", res['worst_post'].get('post_id'))
        else:
            logging.info("%s", res.get("message", "Sin datos suficientes."))
    elif review_type == "weekly":
        logging.info("=== REVISIÓN SEMANAL DE MÉTRICAS (Sección 13.5) ===")
        res = scoreboard.generate_weekly_review()
        if res.get("status") == "ok":
            logging.info("Total publicaciones analizadas: %d", res['total_analyzed'])
            logging.info("Medianas por Pilar: %s", res['pillar_medians'])
            logging.info("Medianas por Plataforma: %s", res['platform_medians'])
            logging.info("Top 3 Posts: %s", [p.get('post_id') for p in res['top_3']])
            logging.info("Bottom 3 Posts: %s", [p.get('post_id') for p in res['bottom_3']])
        else:
            logging.info("Se necesitan al menos 3 publicaciones registradas para la revisión semanal.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube AI Bot & GTA 6 Clipping Page Automation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--module",
        choices=["gta6", "mystery", "reddit", "bizarre", "news", "all"],
        default="gta6",
        help="Módulo temático a ejecutar.",
    )
    parser.add_argument(
        "--pillar",
        choices=["news", "tips", "clip"],
        default="news",
        help="Pilar específico para el módulo GTA 6 (news: Noticias/Facts, tips: HOW-TOs, clip: Highlights).",
    )
    parser.add_argument(
        "--test-name",
        default="Baseline test",
        help="Nombre de la variable testeada en este post (Sección 13 del SOP).",
    )
    parser.add_argument(
        "--clip-url",
        default=None,
        help="URL directa de un clip viral de Twitter/X, TikTok o YouTube para procesar.",
    )
    parser.add_argument(
        "--review",
        choices=["daily", "weekly"],
        default=None,
        help="Ejecuta la revisión analítica diaria o semanal del Scoreboard.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera el video y mantiene archivos temporales sin subir a plataformas.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Genera el video y limpia temporales, pero no realiza la subida.",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Ruta al archivo de configuración YAML.",
    )
    parser.add_argument(
        "--log-file",
        default="logs/bot.log",
        help="Ruta al archivo de registro de logs.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Habilita mensajes de depuración detallados (DEBUG).",
    )

    args = parser.parse_args()

    # Iniciar Logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(args.log_file, level=log_level)

    logging.info("==================================================")
    logging.info("YouTube AI Bot & GTA 6 Clipping Page")
    logging.info("==================================================")

    if args.review:
        handle_review(args.review)
        return

    logging.info("Módulo objetivo: %s | Pilar: %s", args.module, args.pillar)
    logging.info("Modo dry-run: %s | Modo no-upload: %s", args.dry_run, args.no_upload)

    # Cargar Configuración
    config = load_global_config(args.config)

    # Ejecución
    if args.module == "all":
        results = {}
        for pillar in ["news", "tips", "clip"]:
            success = run_pipeline("gta6", config, dry_run=args.dry_run, no_upload=args.no_upload, pillar=pillar, test_name=args.test_name)
            results[f"gta6_{pillar}"] = success

        logging.info("==================================================")
        logging.info("Resumen de ejecución global:")
        all_passed = True
        for mod, ok in results.items():
            status_str = "EXITOSO ✅" if ok else "FALLIDO ❌"
            logging.info("  - %s: %s", mod, status_str)
            if not ok:
                all_passed = False
        logging.info("==================================================")

        if not all_passed:
            sys.exit(1)
    else:
        success = run_pipeline(
            args.module,
            config,
            dry_run=args.dry_run,
            no_upload=args.no_upload,
            pillar=args.pillar,
            test_name=args.test_name,
            clip_url=args.clip_url,
        )
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
