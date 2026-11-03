"""Entry point principal de YouTube AI Bot.

Permite ejecutar bajo demanda cualquier módulo del pipeline de generación de Shorts:
- mystery: Historias de terror y misterio
- news: Noticias y curiosidades virales
- reddit: Reddit Stories en primera persona
- all: Ejecuta los tres módulos en secuencia

Uso:
    python main.py --module mystery
    python main.py --module news --dry-run
    python main.py --module reddit --no-upload
    python main.py --module all --dry-run
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


def run_pipeline(module_name: str, config: Dict[str, Any], dry_run: bool, no_upload: bool) -> bool:
    """Ejecuta un módulo específico y retorna True si tuvo éxito."""
    from src.modules import mystery, news, reddit, bizarre

    modules_map = {
        "mystery": mystery.run,
        "reddit": reddit.run,
        "bizarre": bizarre.run,
        "news": news.run,
    }

    if module_name not in modules_map:
        logging.error("Módulo desconocido: '%s'. Opciones válidas: %s", module_name, list(modules_map.keys()))
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube AI Bot — Automatización de YouTube Shorts",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--module",
        choices=["mystery", "reddit", "bizarre", "news", "all"],
        default="mystery",
        help="Módulo temático a ejecutar.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera el video y mantiene archivos temporales sin subir a YouTube.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Genera el video y limpia temporales, pero no realiza la subida a YouTube.",
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
    logging.info("YouTube AI Bot — Inicio de Ejecución")
    logging.info("Módulo objetivo: %s", args.module)
    logging.info("Modo dry-run: %s | Modo no-upload: %s", args.dry_run, args.no_upload)
    logging.info("==================================================")

    # Cargar Configuración
    config = load_global_config(args.config)

    # Ejecución
    if args.module == "all":
        results = {}
        for mod in ["mystery", "news", "reddit"]:
            success = run_pipeline(mod, config, dry_run=args.dry_run, no_upload=args.no_upload)
            results[mod] = success

        logging.info("==================================================")
        logging.info("Resumen de ejecución global:")
        all_passed = True
        for mod, ok in results.items():
            status_str = "EXITOSO ✅" if ok else "FALLIDO ❌"
            logging.info("  - %s: %s", mod.capitalize(), status_str)
            if not ok:
                all_passed = False
        logging.info("==================================================")

        if not all_passed:
            sys.exit(1)
    else:
        success = run_pipeline(args.module, config, dry_run=args.dry_run, no_upload=args.no_upload)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
