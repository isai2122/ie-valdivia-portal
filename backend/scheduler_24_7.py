"""
scheduler_24_7.py — MetanoSRGAN Elite v3.5
Scheduler que ejecuta el pipeline de detección cada 3 horas (24/7).
Diseñado para correr como proceso en background o servicio systemd.
"""

import os
import sys
import time
import json
import logging
import schedule
import threading
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from sentinel5p_downloader import Sentinel5PDownloader
from detection_pipeline_v35 import MetanoDetectionPipeline

# ─── Configuración de logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/ubuntu/metanosrgan_v35/logs/scheduler.log"),
    ],
)
logger = logging.getLogger("scheduler_24_7")

DATA_DIR = "/home/ubuntu/metanosrgan_v35/data"
TICKETS_DIR = "/home/ubuntu/metanosrgan_v35/tickets"
LOGS_DIR = "/home/ubuntu/metanosrgan_v35/logs"

# ─── Instancias ───────────────────────────────────────────────────────────────
downloader = Sentinel5PDownloader(data_dir=DATA_DIR)
pipeline = MetanoDetectionPipeline(
    data_dir=DATA_DIR,
    tickets_dir=TICKETS_DIR,
    logs_dir=LOGS_DIR,
)

_running = False


def run_detection_cycle():
    """Ejecuta un ciclo completo de detección."""
    global _running
    if _running:
        logger.warning("Ciclo anterior aún en ejecución, omitiendo...")
        return

    _running = True
    start_time = datetime.now(timezone.utc)
    logger.info(f"=== CICLO DE DETECCIÓN 24/7 INICIADO: {start_time.isoformat()} ===")

    try:
        # 1. Descargar datos reales de Sentinel-5P
        logger.info("Paso 1/2: Descargando datos de Sentinel-5P...")
        detections = downloader.scan_zone_for_methane()
        logger.info(f"  → {len(detections)} puntos escaneados")

        # 2. Ejecutar pipeline completo
        logger.info("Paso 2/2: Ejecutando pipeline de detección...")
        report = pipeline.run_full_pipeline(detections)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"=== CICLO COMPLETADO en {elapsed:.1f}s ===\n"
            f"  Alertas certificadas: {report['total_certificadas']}\n"
            f"  Alertas ÉLITE: {report['total_alertas_elite']}\n"
            f"  Elite Score máximo: {report['elite_score_maximo']}\n"
            f"  Pérdida detectada: ${report['perdida_total_usd_dia']} USD/día\n"
            f"  Tickets generados: {report['tickets_generados']}"
        )

        # Notificar si hay alertas críticas
        if report["total_alertas_elite"] > 0:
            logger.warning(
                f"⚠️  ALERTA ÉLITE: {report['total_alertas_elite']} fugas críticas detectadas! "
                f"Elite Score máximo: {report['elite_score_maximo']}"
            )

    except Exception as e:
        logger.error(f"Error en ciclo de detección: {e}", exc_info=True)
    finally:
        _running = False


def run_health_check():
    """Verifica el estado de salud del sistema."""
    status_path = os.path.join(DATA_DIR, "IA_STATUS_24_7.json")
    if os.path.exists(status_path):
        with open(status_path) as f:
            status = json.load(f)
        logger.info(
            f"Health Check: {status.get('system_status')} | "
            f"Última ejecución: {status.get('last_execution', 'N/A')[:19]}"
        )
    else:
        logger.warning("Health Check: Sin datos de estado disponibles")


def start_scheduler():
    """Configura y arranca el scheduler 24/7."""
    logger.info("MetanoSRGAN Elite v3.5 — Scheduler 24/7 iniciando...")
    logger.info("Configuración: Ciclos cada 3 horas | Health check cada hora")

    # Ejecutar inmediatamente al arrancar
    logger.info("Ejecutando ciclo inicial...")
    run_detection_cycle()

    # Programar ciclos cada 3 horas
    schedule.every(3).hours.do(run_detection_cycle)

    # Health check cada hora
    schedule.every(1).hours.do(run_health_check)

    logger.info("Scheduler activo. Próximos ciclos programados:")
    for job in schedule.jobs:
        logger.info(f"  → {job}")

    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar cada minuto


if __name__ == "__main__":
    start_scheduler()
