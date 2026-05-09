"""
tRPC-compatible router para MetanoSRGAN Elite v5.2
Enfoque 100% Datos Reales - Magdalena Medio.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.routes import get_current_user
from app.models.user import UserInDB
from app.core.cache import cached
from app.services.predictive_engine import PredictiveEngine
from app.services.gis_exporter import GISExporter

router = APIRouter(prefix="/trpc", tags=["tRPC"])

# Servicios v5.2 (Datos Reales)
predictive_engine = PredictiveEngine()
gis_exporter = GISExporter()

_EVENTS_FILE = Path("/home/ubuntu/metanosrgan_v50/backend/data/events_real.json")

def _load_events() -> List[Dict]:
    if _EVENTS_FILE.exists():
        with open(_EVENTS_FILE, "r") as f:
            return json.load(f)
    return []

class TRPCResponse(BaseModel):
    result: Any
    ok: bool = True

@router.get("/stats.overview", response_model=TRPCResponse)
@cached("stats.overview", ttl_seconds=300)
async def stats_overview(current_user: UserInDB = Depends(get_current_user)):
    events = _load_events()
    total = len(events)
    critical = sum(1 for e in events if "CRÍTICA" in e.get("categoria_alerta", ""))
    ppbs = [e.get("intensidad_ppb", 0) for e in events]
    avg_ppb = sum(ppbs) / len(ppbs) if ppbs else 0
    
    return TRPCResponse(result={
        "total_detections": total,
        "critical_alerts": critical,
        "avg_ppb": round(avg_ppb, 2),
        "last_updated": datetime.utcnow().isoformat(),
    })

@router.get("/analytics.recurrence", response_model=TRPCResponse)
@cached("analytics.recurrence", ttl_seconds=3600)
async def get_recurrence(current_user: UserInDB = Depends(get_current_user)):
    """Análisis de recurrencia histórica real"""
    return TRPCResponse(result=predictive_engine.analyze_real_recurrence())

@router.get("/export.geojson", response_model=TRPCResponse)
async def export_geojson(current_user: UserInDB = Depends(get_current_user)):
    """Exportar los 409 puntos reales a GeoJSON"""
    return TRPCResponse(result=gis_exporter.to_geojson())

@router.get("/alerts.heatmap", response_model=TRPCResponse)
async def alerts_heatmap(current_user: UserInDB = Depends(get_current_user)):
    events = _load_events()
    points = [
        {
            "lat": e["latitud"], 
            "lng": e["longitud"], 
            "intensity": e.get("intensidad_ppb", 0), 
            "station": e.get("activo_cercano", "")
        } 
        for e in events if "latitud" in e and "longitud" in e
    ]
    return TRPCResponse(result=points)

@router.get("/model.status", response_model=TRPCResponse)
async def model_status(current_user: UserInDB = Depends(get_current_user)):
    return TRPCResponse(result={
        "name": "MetanoSRGAN Elite",
        "version": "v5.2",
        "status": "operational",
        "data_points": 409
    })
