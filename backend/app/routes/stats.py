"""Stats de overview para la home del dashboard — v5.0 con datos reales del Drive."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.db.mongo import get_db
from app.models.stats import StatsOverview, TimeseriesPoint
from app.models.user import UserPublic
from app.services.drive_sync import get_events, get_statistics

router = APIRouter(prefix="/stats", tags=["stats"])


def _parse(iso_str: str):
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


@router.get("/overview", response_model=StatsOverview)
async def overview(_user: UserPublic = Depends(get_current_user)) -> StatsOverview:
    """
    Overview enriquecido con datos reales del Drive (Sentinel-5P).
    Combina datos de MongoDB (simulados) con datos reales del JSON del Drive.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    cut24 = now - timedelta(hours=24)
    cut7  = now - timedelta(days=7)

    # ── Datos de MongoDB (simulados) ──────────────────────────────────────────
    total_mongo = await db.detections.count_documents({})
    last24 = await db.detections.count_documents(
        {"detected_at": {"$gte": cut24.isoformat().replace("+00:00", "Z")}}
    )
    stations_count = await db.stations.count_documents({})
    active_alerts = await db.alerts.count_documents({"acknowledged": False})
    critical_alerts = await db.alerts.count_documents(
        {"severity": "critical", "acknowledged": False}
    )

    # ── Datos reales del Drive ────────────────────────────────────────────────
    real_stats = get_statistics()
    real_events = get_events()

    # Usar datos reales si están disponibles, sino fallback a MongoDB
    total = real_stats["total"] if real_stats["total"] > 0 else total_mongo

    # Timeseries 30d desde datos reales
    iso_cut30 = (now - timedelta(days=30))
    buckets: dict[str, list] = {}
    for i in range(30):
        day = (now - timedelta(days=29 - i)).date().isoformat()
        buckets[day] = [0, 0.0]

    for e in real_events:
        try:
            t = datetime.fromisoformat(e["fecha_deteccion"].replace("Z", ""))
            if t >= iso_cut30.replace(tzinfo=None):
                day = t.date().isoformat()
                if day in buckets:
                    buckets[day][0] += 1
                    buckets[day][1] += float(e.get("intensidad_ppb", 0))
        except Exception:
            continue

    # Fallback a MongoDB si no hay datos reales en timeseries
    if all(v[0] == 0 for v in buckets.values()):
        iso_cut30_str = iso_cut30.isoformat().replace("+00:00", "Z")
        recent_mongo = await db.detections.find(
            {"detected_at": {"$gte": iso_cut30_str}},
            {"_id": 0, "detected_at": 1, "concentration_ppb": 1, "severity": 1},
        ).to_list(20000)
        for d in recent_mongo:
            try:
                t = _parse(d["detected_at"])
                day = t.date().isoformat()
                if day in buckets:
                    buckets[day][0] += 1
                    buckets[day][1] += float(d.get("concentration_ppb", 0))
            except Exception:
                continue

    series: List[TimeseriesPoint] = []
    for day, (cnt, s) in buckets.items():
        series.append(TimeseriesPoint(
            date=day, count=cnt, avg_ppb=round(s / cnt, 1) if cnt else 0.0,
        ))

    # avg_ppb_last_7d desde datos reales
    ppbs_7d = [
        e.get("intensidad_ppb", 0)
        for e in real_events
        if datetime.fromisoformat(e.get("fecha_deteccion", "2000-01-01").replace("Z", "")) >= cut7.replace(tzinfo=None)
    ]
    avg7 = round(sum(ppbs_7d) / len(ppbs_7d), 1) if ppbs_7d else real_stats.get("avg_ppb", 0)

    # detections_by_severity desde datos reales
    by_sev_d = {
        "info": real_stats.get("routine", 0),
        "warning": real_stats.get("preventive", 0),
        "critical": real_stats.get("critical", 0),
    }

    return StatsOverview(
        total_detections=total,
        detections_last_24h=last24,
        active_alerts=active_alerts or real_stats.get("preventive", 0),
        critical_alerts=critical_alerts or real_stats.get("critical", 0),
        stations_count=stations_count or 5,
        avg_ppb_last_7d=avg7,
        detections_by_severity=by_sev_d,
        detections_timeseries_30d=series,
    )
