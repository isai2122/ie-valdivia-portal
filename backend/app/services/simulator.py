"""Simulador de alertas. Inyecta detecciones+alerts periódicamente.

ES UN SIMULADOR. No usa el modelo. Controlable por SIMULATE_ALERTS.
"""
import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.db.mongo import get_db
from app.models.alert import Alert
from app.models.detection import Detection
from app.services.plume import make_plume_polygon
from app.ws.manager import manager

log = logging.getLogger("simulator")


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _rand_severity() -> str:
    r = random.random()
    if r < 0.6: return "info"
    if r < 0.9: return "warning"
    return "critical"


async def _tick() -> None:
    db = get_db()
    min_lng, min_lat, max_lng, max_lat = settings.mm_bbox
    lat = random.uniform(min_lat + 0.3, max_lat - 0.3)
    lng = random.uniform(min_lng + 0.3, max_lng - 0.3)
    sev = _rand_severity()
    if sev == "critical":
        ppb = random.uniform(2400, 2800); area = random.uniform(3.5, 8.0); conf = random.uniform(0.82, 0.97)
    elif sev == "warning":
        ppb = random.uniform(2050, 2400); area = random.uniform(1.2, 3.5); conf = random.uniform(0.7, 0.9)
    else:
        ppb = random.uniform(1800, 2050); area = random.uniform(0.1, 1.2); conf = random.uniform(0.55, 0.78)

    wind_dir = random.uniform(30, 110)
    det = Detection(
        id=f"det-{uuid.uuid4().hex[:10]}",
        detected_at=_iso(datetime.now(timezone.utc)),
        lat=round(lat, 5), lng=round(lng, 5),
        concentration_ppb=round(ppb, 1),
        plume_area_km2=round(area, 2),
        confidence=round(conf, 3),
        wind_direction_deg=round(wind_dir, 1),
        wind_speed_ms=round(random.uniform(1.2, 5.5), 2),
        severity=sev, status="new",
        sentinel_scene_id=f"SIM_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}",
        plume_geojson=make_plume_polygon(lat, lng, area, wind_dir, vertices=12),
    )
    await db.detections.insert_one(det.model_dump())

    alert = Alert(
        id=f"alert-{uuid.uuid4().hex[:10]}",
        detection_id=det.id,
        created_at=_iso(datetime.now(timezone.utc)),
        severity=sev,
        title=f"[simulador] Pluma {round(ppb, 0)} ppb",
        message=f"Detección sintética {round(area,1)} km² en bbox Magdalena Medio.",
    )
    await db.alerts.insert_one(alert.model_dump())

    await manager.broadcast({
        "type": "alert.created",
        "alert": alert.model_dump(),
        "detection": det.model_dump(),
        "source": "simulator",
    })
    log.info("simulator emitted alert %s (%s)", alert.id, sev)


async def run_simulator_loop() -> None:
    """Corre hasta que la app se apague. Primera emisión acelerada para tests."""
    if not settings.simulate_alerts:
        log.info("simulator disabled (SIMULATE_ALERTS=false)")
        return
    log.info(
        "simulator loop started (interval %d-%d s)",
        settings.simulator_min_interval_s, settings.simulator_max_interval_s,
    )
    # Primera emisión rápida (5-15s) para no esperar el intervalo completo.
    await asyncio.sleep(random.uniform(5.0, 15.0))
    try:
        while True:
            try:
                await _tick()
            except Exception:  # noqa: BLE001
                log.exception("simulator tick failed")
            wait = random.uniform(
                settings.simulator_min_interval_s, settings.simulator_max_interval_s
            )
            await asyncio.sleep(wait)
    except asyncio.CancelledError:
        log.info("simulator loop cancelled")
        raise
