"""
api_server_v35.py — MetanoSRGAN Elite v3.5
API REST FastAPI completa para el sistema de detección de metano 24/7.
Endpoints para dashboard, detecciones, tickets, estado del sistema y ejecución manual.
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Añadir directorio al path
sys.path.insert(0, os.path.dirname(__file__))

from sentinel5p_downloader import Sentinel5PDownloader
from detection_pipeline_v35 import MetanoDetectionPipeline

# ─── Configuración ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/ubuntu/metanosrgan_v35/logs/api_server.log"),
    ],
)
logger = logging.getLogger(__name__)

DATA_DIR = "/home/ubuntu/metanosrgan_v35/data"
TICKETS_DIR = "/home/ubuntu/metanosrgan_v35/tickets"
LOGS_DIR = "/home/ubuntu/metanosrgan_v35/logs"
FRONTEND_DIR = "/home/ubuntu/metanosrgan_v35/frontend"

# ─── Instancias globales ──────────────────────────────────────────────────────
downloader = Sentinel5PDownloader(data_dir=DATA_DIR)
pipeline = MetanoDetectionPipeline(
    data_dir=DATA_DIR,
    tickets_dir=TICKETS_DIR,
    logs_dir=LOGS_DIR,
)

# ─── App FastAPI ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="MetanoSRGAN Elite v3.5",
    description="Sistema de Detección de Metano 24/7 a 10 metros — Magdalena Medio, Colombia",
    version="3.5.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global del pipeline (para evitar ejecuciones concurrentes)
_pipeline_running = False
_last_report: Optional[Dict] = None


# ─── Modelos Pydantic ─────────────────────────────────────────────────────────
class PipelineStatus(BaseModel):
    running: bool
    last_execution: Optional[str]
    system_status: str


class DetectionSummary(BaseModel):
    total_alertas: int
    alertas_elite: int
    perdida_usd_dia: float
    co2e_ton_year: float
    elite_score_max: float


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _load_status() -> Dict:
    status_path = os.path.join(DATA_DIR, "IA_STATUS_24_7.json")
    if os.path.exists(status_path):
        with open(status_path) as f:
            return json.load(f)
    return {
        "system_status": "INITIALIZING",
        "version": "3.5",
        "last_execution": None,
        "next_check": None,
        "last_results": {
            "total_alertas": 0,
            "alertas_criticas_elite_score_80": 0,
            "perdida_total_usd_dia": 0,
            "impacto_co2e_anual_ton": 0,
            "elite_score_maximo": 0,
        },
    }


def _load_latest_report() -> Optional[Dict]:
    """Carga el reporte operativo más reciente."""
    reports = sorted(Path(DATA_DIR).glob("reporte_operativo_*.json"), reverse=True)
    if reports:
        with open(reports[0]) as f:
            return json.load(f)
    return None


def _load_event_history(limit: int = 500) -> List[Dict]:
    """Carga el historial de eventos."""
    master_path = os.path.join(DATA_DIR, "event_master_table.json")
    if os.path.exists(master_path):
        with open(master_path) as f:
            data = json.load(f)
        return data[-limit:]
    return []


async def _run_pipeline_async():
    """Ejecuta el pipeline de detección en background."""
    global _pipeline_running, _last_report
    if _pipeline_running:
        logger.warning("Pipeline ya en ejecución, omitiendo...")
        return

    _pipeline_running = True
    try:
        logger.info("Iniciando pipeline de detección 24/7...")
        loop = asyncio.get_event_loop()

        # Ejecutar en thread pool para no bloquear el event loop
        detections = await loop.run_in_executor(None, downloader.scan_zone_for_methane)
        report = await loop.run_in_executor(None, pipeline.run_full_pipeline, detections)
        _last_report = report
        logger.info(f"Pipeline completado: {report['total_certificadas']} alertas certificadas")
    except Exception as e:
        logger.error(f"Error en pipeline: {e}", exc_info=True)
    finally:
        _pipeline_running = False


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Estado de salud del sistema."""
    status = _load_status()
    return {
        "status": "ok",
        "version": "3.5",
        "system_status": status.get("system_status", "UNKNOWN"),
        "pipeline_running": _pipeline_running,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": "Copernicus Sentinel-5P + Open-Meteo",
        "coverage": "Magdalena Medio, Colombia",
        "resolution": "10m (Super-Resolución)",
        "update_frequency": "Cada 3 horas (24/7)",
    }


@app.get("/api/status")
async def get_system_status():
    """Estado operativo completo del sistema."""
    status = _load_status()
    status["pipeline_running"] = _pipeline_running
    return status


@app.post("/api/pipeline/run")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Dispara manualmente el pipeline de detección."""
    if _pipeline_running:
        return {"message": "Pipeline ya en ejecución", "running": True}

    background_tasks.add_task(_run_pipeline_async)
    return {
        "message": "Pipeline iniciado",
        "running": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/detections/latest")
async def get_latest_detections(limit: int = Query(50, ge=1, le=200)):
    """Retorna las detecciones más recientes del último reporte."""
    report = _load_latest_report()
    if not report:
        # Si no hay reporte, ejecutar pipeline
        return {"detections": [], "message": "Sin datos. Use POST /api/pipeline/run para iniciar."}

    detections = report.get("detecciones", [])[:limit]
    return {
        "total": len(detections),
        "timestamp": report.get("timestamp"),
        "detections": detections,
    }


@app.get("/api/detections/elite")
async def get_elite_detections():
    """Retorna solo las detecciones con Elite Score ≥ 80."""
    report = _load_latest_report()
    if not report:
        return {"detections": [], "message": "Sin datos disponibles"}

    elite = [d for d in report.get("detecciones", []) if d.get("elite_score", 0) >= 80]
    return {
        "total": len(elite),
        "timestamp": report.get("timestamp"),
        "detections": elite,
    }


@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Resumen ejecutivo para el dashboard."""
    status = _load_status()
    report = _load_latest_report()
    history = _load_event_history(limit=100)

    # Calcular tendencia (últimos 7 días)
    trend_data = []
    for i in range(7, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        day_events = [
            e for e in history
            if e.get("fecha_deteccion", "")[:10] == day
        ]
        trend_data.append({
            "date": day,
            "alertas": len(day_events),
            "elite": sum(1 for e in day_events if e.get("score_prioridad", 0) >= 80),
            "perdida_usd": round(sum(e.get("perdida_economica_usd_dia", 0) for e in day_events), 2),
        })

    last_results = status.get("last_results", {})

    return {
        "system_status": status.get("system_status", "UNKNOWN"),
        "version": "3.5",
        "last_execution": status.get("last_execution"),
        "next_check": status.get("next_check"),
        "pipeline_running": _pipeline_running,
        "summary": {
            "total_alertas": last_results.get("total_alertas", 0),
            "alertas_elite": last_results.get("alertas_criticas_elite_score_80", 0),
            "perdida_usd_dia": last_results.get("perdida_total_usd_dia", 0),
            "co2e_ton_year": last_results.get("impacto_co2e_anual_ton", 0),
            "elite_score_max": last_results.get("elite_score_maximo", 0),
        },
        "trend_7days": trend_data,
        "total_events_history": len(history),
        "coverage": {
            "zona": "Magdalena Medio, Colombia",
            "activos_monitoreados": 10,
            "resolution_m": 10,
            "fuente_datos": "Sentinel-5P (ESA/Copernicus)",
            "viento": "Open-Meteo (tiempo real)",
        },
    }


@app.get("/api/tickets")
async def list_tickets():
    """Lista todos los tickets de intervención generados."""
    tickets = []
    for f in sorted(Path(TICKETS_DIR).glob("ticket_*.md"), reverse=True):
        stat = f.stat()
        tickets.append({
            "filename": f.name,
            "ticket_id": f.name.split("_")[1] if "_" in f.name else f.name,
            "created": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "size_bytes": stat.st_size,
        })
    return {"total": len(tickets), "tickets": tickets[:50]}


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Retorna el contenido de un ticket específico."""
    for f in Path(TICKETS_DIR).glob(f"ticket_{ticket_id}_*.md"):
        with open(f, encoding="utf-8") as fh:
            return {"ticket_id": ticket_id, "content": fh.read(), "filename": f.name}
    raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado")


@app.get("/api/history")
async def get_history(
    limit: int = Query(100, ge=1, le=1000),
    activo: Optional[str] = None,
):
    """Historial completo de detecciones."""
    history = _load_event_history(limit=limit * 2)

    if activo:
        history = [e for e in history if activo.lower() in e.get("activo_cercano", "").lower()]

    return {
        "total": len(history),
        "events": history[:limit],
    }


@app.get("/api/wind/{lat}/{lon}")
async def get_wind(lat: float, lon: float):
    """Datos de viento en tiempo real para una coordenada."""
    import asyncio
    loop = asyncio.get_event_loop()
    wind = await loop.run_in_executor(None, downloader.get_wind_data, lat, lon)
    return wind


@app.get("/api/infrastructure")
async def get_infrastructure():
    """Lista de activos de infraestructura monitoreados."""
    from sentinel5p_downloader import INFRAESTRUCTURA_MAGDALENA
    return {
        "total": len(INFRAESTRUCTURA_MAGDALENA),
        "activos": INFRAESTRUCTURA_MAGDALENA,
        "zona": "Magdalena Medio, Colombia",
    }


@app.get("/api/report/latest")
async def get_latest_report():
    """Reporte operativo más reciente completo."""
    report = _load_latest_report()
    if not report:
        return {"message": "Sin reportes disponibles. Use POST /api/pipeline/run"}
    return report


# ─── Arranque automático del pipeline ────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Al iniciar el servidor, ejecutar el pipeline si no hay datos recientes."""
    logger.info("MetanoSRGAN Elite v3.5 iniciando...")
    status = _load_status()
    last_exec = status.get("last_execution")

    should_run = True
    if last_exec:
        try:
            last_dt = datetime.fromisoformat(last_exec)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            if age_hours < 3:
                should_run = False
                logger.info(f"Datos recientes ({age_hours:.1f}h), omitiendo ejecución inicial")
        except Exception:
            pass

    if should_run:
        logger.info("Ejecutando pipeline inicial...")
        asyncio.create_task(_run_pipeline_async())


# ─── Servir frontend estático ─────────────────────────────────────────────────
if os.path.exists(FRONTEND_DIR) and os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server_v35:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
