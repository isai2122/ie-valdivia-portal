"""
Servicio de sincronización con Google Drive — MetanoSRGAN Elite v5.0
Lee datos reales de eventos de metano desde el archivo JSON del Drive.
En producción, usa la API de Google Drive para sincronización automática.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("metavision.drive_sync")

# Ruta al archivo de datos reales (cargado desde el Drive)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_FILE = DATA_DIR / "events_real.json"
SYNC_META_FILE = DATA_DIR / "sync_meta.json"

# Cache en memoria
_events_cache: Optional[List[Dict]] = None
_sync_meta: Optional[Dict] = None


def _load_sync_meta() -> Dict:
    global _sync_meta
    if _sync_meta is None:
        if SYNC_META_FILE.exists():
            with open(SYNC_META_FILE, "r") as f:
                _sync_meta = json.load(f)
        else:
            _sync_meta = {
                "last_sync": "2026-04-27T23:58:36Z",
                "source_file": "event_master_table_ACTUALIZADA_27_ABRIL.json",
                "drive_folder": "MetanoSRGAN Elite",
                "events_count": 0,
                "sync_interval_min": 60,
                "data_freshness": "real",
            }
    return _sync_meta


def get_events() -> List[Dict]:
    """Retorna todos los eventos de metano cargados desde el Drive."""
    global _events_cache
    if _events_cache is None:
        if EVENTS_FILE.exists():
            try:
                with open(EVENTS_FILE, "r") as f:
                    _events_cache = json.load(f)
                log.info("Loaded %d events from %s", len(_events_cache), EVENTS_FILE)
            except Exception as e:
                log.error("Failed to load events: %s", e)
                _events_cache = []
        else:
            log.warning("Events file not found: %s", EVENTS_FILE)
            _events_cache = []
    return _events_cache


def get_sync_status() -> Dict:
    """Retorna el estado de sincronización con Google Drive."""
    meta = _load_sync_meta()
    events = get_events()
    return {
        **meta,
        "events_loaded": len(events),
        "connected": len(events) > 0,
    }


def get_statistics() -> Dict:
    """Calcula estadísticas globales de los eventos."""
    events = get_events()
    if not events:
        return {
            "total": 0,
            "critical": 0,
            "preventive": 0,
            "routine": 0,
            "avg_ppb": 0,
            "max_ppb": 0,
            "stations": [],
        }

    ppbs = [e.get("intensidad_ppb", 0) for e in events]
    stations = list(set(e.get("activo_cercano", "") for e in events if e.get("activo_cercano")))

    return {
        "total": len(events),
        "critical": sum(1 for e in events if "CRÍTICA" in e.get("categoria_alerta", "")),
        "preventive": sum(1 for e in events if "PREVENTIVA" in e.get("categoria_alerta", "")),
        "routine": sum(1 for e in events if "RUTINARIO" in e.get("categoria_alerta", "")),
        "avg_ppb": round(sum(ppbs) / len(ppbs), 2) if ppbs else 0,
        "max_ppb": round(max(ppbs), 2) if ppbs else 0,
        "stations": stations,
        "computed_at": datetime.utcnow().isoformat(),
    }


def refresh_cache() -> bool:
    """Fuerza la recarga del caché desde el archivo."""
    global _events_cache, _sync_meta
    _events_cache = None
    _sync_meta = None
    events = get_events()
    log.info("Cache refreshed: %d events loaded", len(events))
    return len(events) > 0
