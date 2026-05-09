"""Seed completo Fase 1: usuarios, stations, wells, pipelines, detections,
wind samples, alerts. Idempotente. CLI `python -m app.db.seed --reset`."""
from __future__ import annotations

import argparse
import asyncio
import logging
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

log = logging.getLogger("seed")

# --------- Users ---------
SEED_USERS = [
    {"email": "admin@metanosrgan.co",    "password": "Admin123!",    "name": "Isai Admin",    "role": "admin"},
    {"email": "analista@metanosrgan.co", "password": "Analista123!", "name": "Ana Lista",     "role": "analyst"},
    {"email": "visor@metanosrgan.co",    "password": "Visor123!",    "name": "Vicente Visor", "role": "viewer"},
]

# --------- Stations (extendidas Fase 1) ---------
SEED_STATIONS = [
    {"id": "station-barrancabermeja", "name": "Barrancabermeja", "municipality": "Barrancabermeja",
     "department": "Santander", "lat": 7.0653, "lng": -73.8547, "operator": "Ecopetrol",
     "capacity_mmscfd": 500.0, "installation_year": 1951, "risk_level": "high"},
    {"id": "station-vasconia",        "name": "Vasconia",        "municipality": "Puerto Boyacá",
     "department": "Boyacá",    "lat": 5.9833, "lng": -74.4667, "operator": "TGI",
     "capacity_mmscfd": 280.0, "installation_year": 1988, "risk_level": "high"},
    {"id": "station-mariquita",       "name": "Mariquita",       "municipality": "Mariquita",
     "department": "Tolima",    "lat": 5.2000, "lng": -74.8833, "operator": "TGI",
     "capacity_mmscfd": 180.0, "installation_year": 1995, "risk_level": "medium"},
    {"id": "station-malena",          "name": "Malena",          "municipality": "Puerto Nare",
     "department": "Antioquia", "lat": 6.1908, "lng": -74.5878, "operator": "TGI",
     "capacity_mmscfd": 120.0, "installation_year": 2001, "risk_level": "medium"},
    {"id": "station-miraflores",      "name": "Miraflores",      "municipality": "Miraflores",
     "department": "Boyacá",    "lat": 5.1975, "lng": -73.1464, "operator": "TGI",
     "capacity_mmscfd":  90.0, "installation_year": 2008, "risk_level": "low"},
]

# --------- Wells (campos reales del Magdalena Medio, coords aprox) ---------
# (name, lat, lng, dept, muni, operator, type, status)
WELL_SEEDS = [
    ("La Cira-1",        6.5667, -73.7500, "Santander", "Barrancabermeja", "Ecopetrol", "oil",  "active"),
    ("La Cira-47",       6.5820, -73.7660, "Santander", "Barrancabermeja", "Ecopetrol", "oil",  "active"),
    ("Infantas-2",       6.5512, -73.7281, "Santander", "Barrancabermeja", "Ecopetrol", "oil",  "active"),
    ("Infantas-14",      6.5444, -73.7103, "Santander", "Barrancabermeja", "Ecopetrol", "dual", "active"),
    ("Casabe-A1",        6.7700, -74.0220, "Santander", "Yondó",           "Ecopetrol", "oil",  "active"),
    ("Casabe-B7",        6.7890, -74.0110, "Santander", "Yondó",           "Ecopetrol", "oil",  "active"),
    ("Yarigui-CT-1",     7.0211, -73.9520, "Santander", "Cantagallo",      "Ecopetrol", "oil",  "active"),
    ("Yarigui-CT-5",     7.0118, -73.9667, "Santander", "Cantagallo",      "Ecopetrol", "oil",  "suspended"),
    ("Lizama-1",         6.7800, -73.4100, "Santander", "Girón",           "Ecopetrol", "gas",  "active"),
    ("Lizama-158",       6.7667, -73.4433, "Santander", "Girón",           "Ecopetrol", "gas",  "active"),
    ("Nutria-3",         7.1100, -73.9700, "Santander", "Puerto Wilches",  "Parex",     "oil",  "active"),
    ("Payoa-2",          7.1500, -73.6800, "Santander", "Sabana de Torres","Ecopetrol", "oil",  "active"),
    ("Payoa-11",         7.1620, -73.6611, "Santander", "Sabana de Torres","Ecopetrol", "dual", "active"),
    ("Llanito-12",       7.0330, -73.7780, "Santander", "Barrancabermeja", "Ecopetrol", "oil",  "active"),
    ("Provincia-4",      6.9800, -73.9100, "Santander", "Puerto Wilches",  "Parex",     "gas",  "active"),
    ("Opon-9",           6.8900, -73.7500, "Santander", "Simacota",        "Hocol",     "gas",  "suspended"),
    ("Tisquirama-1",     7.5222, -73.5847, "Cesar",     "La Gloria",       "Ecopetrol", "oil",  "active"),
    ("Cicuco-3",         9.2714, -74.6475, "Bolívar",   "Cicuco",          "Ecopetrol", "gas",  "active"),
    ("Cantagallo-B5",    7.0410, -73.9160, "Santander", "Cantagallo",      "Ecopetrol", "oil",  "active"),
    ("Velásquez-1",      5.9700, -74.3700, "Boyacá",    "Puerto Boyacá",   "GeoPark",   "oil",  "active"),
    ("Velásquez-15",     5.9920, -74.3510, "Boyacá",    "Puerto Boyacá",   "GeoPark",   "oil",  "active"),
    ("Palagua-2",        6.0200, -74.5400, "Boyacá",    "Puerto Boyacá",   "Ecopetrol", "oil",  "abandoned"),
    ("Nare-7",           6.1800, -74.6100, "Antioquia", "Puerto Nare",     "Parex",     "oil",  "active"),
    ("Nare-22",          6.2040, -74.6330, "Antioquia", "Puerto Nare",     "Parex",     "gas",  "active"),
    ("Cristalina-4",     5.7500, -74.4900, "Boyacá",    "Otanche",         "Hocol",     "gas",  "active"),
    ("Moriche-1",        5.8400, -74.6100, "Boyacá",    "Puerto Boyacá",   "Ecopetrol", "dual", "active"),
    ("Tenay-2",          6.8200, -73.3200, "Santander", "Rionegro",        "Parex",     "gas",  "active"),
    ("Sardinas-5",       5.3600, -74.6200, "Tolima",    "Honda",           "GeoPark",   "oil",  "suspended"),
]


# --------- Pipelines: aproximaciones de troncales reales ---------
PIPELINE_SEEDS = [
    {
        "id": "pipeline-ballena-barranca",
        "name": "Gasoducto Ballena — Barrancabermeja",
        "operator": "Promigas",
        "diameter_inches": 18.0,
        "length_km": 578.0,
        "coordinates": [
            [-72.7000, 11.7500], [-73.1000, 10.8000],
            [-73.3500,  9.9000], [-73.5500,  9.0000],
            [-73.7200,  8.2500], [-73.8547,  7.0653],
        ],
        "status": "active", "pressure_psi": 1200.0,
    },
    {
        "id": "pipeline-barranca-vasconia",
        "name": "Gasoducto Barrancabermeja — Vasconia",
        "operator": "TGI", "diameter_inches": 20.0, "length_km": 197.0,
        "coordinates": [[-73.8547, 7.0653], [-74.1000, 6.6500], [-74.3000, 6.2500], [-74.4667, 5.9833]],
        "status": "active", "pressure_psi": 1150.0,
    },
    {
        "id": "pipeline-vasconia-mariquita",
        "name": "Gasoducto Vasconia — Mariquita",
        "operator": "TGI", "diameter_inches": 14.0, "length_km": 110.0,
        "coordinates": [[-74.4667, 5.9833], [-74.6500, 5.6500], [-74.8833, 5.2000]],
        "status": "active", "pressure_psi": 1000.0,
    },
    {
        "id": "pipeline-mariquita-cali",
        "name": "Gasoducto Mariquita — Cali (parcial)",
        "operator": "TGI", "diameter_inches": 12.0, "length_km": 223.0,
        "coordinates": [[-74.8833, 5.2000], [-75.2000, 4.7500], [-75.5200, 4.2500], [-76.5300, 3.4370]],
        "status": "active", "pressure_psi":  950.0,
    },
    {
        "id": "pipeline-sebastopol-medellin",
        "name": "Gasoducto Sebastopol — Medellín (parcial)",
        "operator": "TGI", "diameter_inches": 10.0, "length_km": 82.0,
        "coordinates": [[-74.4200, 6.4500], [-74.9800, 6.3500], [-75.5700, 6.2500]],
        "status": "active", "pressure_psi":  820.0,
    },
    {
        "id": "pipeline-apiay-porvenir",
        "name": "Gasoducto Apiay — El Porvenir (parcial)",
        "operator": "Ecopetrol", "diameter_inches": 8.0, "length_km": 62.0,
        "coordinates": [[-73.4500, 4.1500], [-73.2500, 4.3500], [-73.1464, 5.1975]],
        "status": "maintenance", "pressure_psi": 700.0,
    },
]


# --------- Helpers ---------

def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _weighted_severity() -> str:
    r = random.random()
    if r < 0.55:
        return "info"
    if r < 0.85:
        return "warning"
    return "critical"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# --------- Async seed funcs ---------

async def ensure_indexes(db) -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.stations.create_index("id", unique=True)
    await db.wells.create_index("id", unique=True)
    await db.pipelines.create_index("id", unique=True)
    await db.detections.create_index("id", unique=True)
    await db.detections.create_index("detected_at")
    await db.detections.create_index("severity")
    await db.alerts.create_index("id", unique=True)
    await db.alerts.create_index("created_at")
    await db.wind_samples.create_index("id", unique=True)
    await db.wind_samples.create_index("sampled_at")
    await db.inference_jobs.create_index("id", unique=True)
    await db.reports.create_index("id", unique=True)


async def seed_users(db) -> None:
    # Import local para evitar requerir módulos en CLI reset sin backend.
    from app.core.security import hash_password
    from app.models.user import UserInDB

    for spec in SEED_USERS:
        email = spec["email"].lower().strip()
        if await db.users.find_one({"email": email}, {"_id": 0}):
            continue
        user = UserInDB(
            email=email, name=spec["name"], role=spec["role"],
            password_hash=hash_password(spec["password"]),
        )
        await db.users.insert_one(user.model_dump())
        log.info("seeded user %s", email)


async def seed_stations(db) -> None:
    """Upsert: garantiza que los campos nuevos existan en documentos viejos."""
    from app.models.station import Station
    for spec in SEED_STATIONS:
        st = Station(**spec).model_dump()
        await db.stations.replace_one({"id": st["id"]}, st, upsert=True)
    log.info("upserted %d stations", len(SEED_STATIONS))


async def seed_wells(db) -> None:
    from app.models.well import Well
    if await db.wells.count_documents({}) >= len(WELL_SEEDS):
        return
    docs = []
    for (name, lat, lng, dept, muni, op, typ, status) in WELL_SEEDS:
        w = Well(
            id=f"well-{name.lower().replace(' ', '-').replace('.', '')}",
            name=name, operator=op, lat=lat, lng=lng,
            type=typ, status=status, department=dept, municipality=muni,
        ).model_dump()
        docs.append(w)
    if docs:
        await db.wells.insert_many(docs)
        log.info("seeded %d wells", len(docs))


async def seed_pipelines(db) -> None:
    from app.models.pipeline import Pipeline
    if await db.pipelines.count_documents({}) >= len(PIPELINE_SEEDS):
        return
    docs = [Pipeline(**p).model_dump() for p in PIPELINE_SEEDS]
    await db.pipelines.insert_many(docs)
    log.info("seeded %d pipelines", len(docs))


async def seed_wind_samples(db) -> None:
    """30 muestras diarias, malla 10x10 sobre bbox del Magdalena Medio."""
    from app.core.config import settings
    from app.models.wind import WindSample

    if await db.wind_samples.count_documents({}) >= 30:
        return

    min_lng, min_lat, max_lng, max_lat = settings.mm_bbox
    rng = random.Random(42)
    lngs = [min_lng + (max_lng - min_lng) * i / 9 for i in range(10)]
    lats = [min_lat + (max_lat - min_lat) * i / 9 for i in range(10)]

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    docs = []
    for d in range(30):
        sampled_at = now - timedelta(days=29 - d)
        # Dirección dominante (NE/E): 45-90° con variación diaria
        dom_dir = 60.0 + rng.gauss(0, 10)
        grid: List[List[float]] = []
        for la in lats:
            for lo in lngs:
                dir_deg = (dom_dir + rng.gauss(0, 15)) % 360.0
                speed = _clamp(rng.gauss(3.0, 1.2), 0.5, 6.5)
                grid.append([round(lo, 4), round(la, 4),
                             round(speed, 2), round(dir_deg, 1)])
        ws = WindSample(
            id=f"wind-{sampled_at.strftime('%Y%m%d')}",
            sampled_at=_iso(sampled_at),
            bbox=[min_lng, min_lat, max_lng, max_lat],
            grid=grid,
        ).model_dump()
        docs.append(ws)
    await db.wind_samples.insert_many(docs)
    log.info("seeded %d wind samples (10x10 grid)", len(docs))


async def seed_detections_and_alerts(db) -> None:
    """60+ detecciones históricas con clustering cerca de infra + alerts."""
    from app.models.alert import Alert
    from app.models.detection import Detection
    from app.services.plume import make_plume_polygon

    if await db.detections.count_documents({}) >= 60:
        return

    # Centros de clustering: estaciones + subset de pozos
    stations = await db.stations.find({}, {"_id": 0}).to_list(100)
    wells = await db.wells.find({}, {"_id": 0}).to_list(500)
    sources = []
    for s in stations:
        sources.append(("station", s["id"], s["lat"], s["lng"], 0.25))
    for w in random.sample(wells, min(12, len(wells))):
        sources.append(("well", w["id"], w["lat"], w["lng"], 0.12))

    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    docs_det, docs_alert = [], []
    n = 72
    for i in range(n):
        kind, sid, c_lat, c_lng, spread = rng.choice(sources)
        # Ruido gaussiano alrededor del centro
        lat = c_lat + rng.gauss(0, spread)
        lng = c_lng + rng.gauss(0, spread * 1.2)
        days_ago = rng.randint(0, 89)
        hours = rng.randint(0, 23)
        ts = now - timedelta(days=days_ago, hours=hours)

        severity = _weighted_severity()
        # ppb y área correlacionados con severidad
        if severity == "critical":
            ppb = rng.uniform(2400, 2800)
            area = rng.uniform(3.5, 8.0)
            conf = rng.uniform(0.82, 0.97)
        elif severity == "warning":
            ppb = rng.uniform(2050, 2400)
            area = rng.uniform(1.2, 3.5)
            conf = rng.uniform(0.7, 0.9)
        else:
            ppb = rng.uniform(1800, 2050)
            area = rng.uniform(0.1, 1.2)
            conf = rng.uniform(0.55, 0.78)

        wind_dir = rng.uniform(30, 110)   # NE/E dominante
        wind_speed = rng.uniform(1.2, 5.5)

        plume = None
        if rng.random() < 0.92:  # ≥ 80% requisito
            plume = make_plume_polygon(
                lat=lat, lng=lng, area_km2=area,
                wind_dir_deg=wind_dir, vertices=rng.choice([8, 12, 16]),
            )

        det = Detection(
            id=f"det-{uuid.uuid4().hex[:10]}",
            detected_at=_iso(ts),
            lat=round(lat, 5), lng=round(lng, 5),
            concentration_ppb=round(ppb, 1),
            plume_area_km2=round(area, 2),
            confidence=round(conf, 3),
            source_station_id=sid if kind == "station" else None,
            source_well_id=sid if kind == "well" else None,
            wind_direction_deg=round(wind_dir, 1),
            wind_speed_ms=round(wind_speed, 2),
            severity=severity,
            status="new",
            sentinel_scene_id=f"S5P_OFFL_L2__CH4_{ts.strftime('%Y%m%dT%H%M')}",
            plume_geojson=plume,
        ).model_dump()
        docs_det.append(det)

        if severity in ("warning", "critical"):
            ack = days_ago > 7 and rng.random() < 0.6
            alert = Alert(
                id=f"alert-{uuid.uuid4().hex[:10]}",
                detection_id=det["id"],
                created_at=_iso(ts + timedelta(minutes=rng.randint(5, 45))),
                severity=severity,
                title=f"Fuga de metano detectada — {round(ppb, 0)} ppb",
                message=(f"Pluma de {round(area, 1)} km² cerca de "
                         f"{sid}. Confianza {round(conf*100)}%."),
                acknowledged=ack,
                acknowledged_by="analista@metanosrgan.co" if ack else None,
                acknowledged_at=_iso(ts + timedelta(hours=rng.randint(1, 24))) if ack else None,
            ).model_dump()
            docs_alert.append(alert)

    await db.detections.insert_many(docs_det)
    if docs_alert:
        await db.alerts.insert_many(docs_alert)
    log.info("seeded %d detections and %d alerts", len(docs_det), len(docs_alert))


async def run_seed(reset: bool = False) -> Dict[str, int]:
    from app.db.mongo import get_db
    db = get_db()

    if reset:
        for coll in ("stations", "wells", "pipelines", "detections",
                     "wind_samples", "alerts", "inference_jobs", "reports"):
            await db.drop_collection(coll)
        log.warning("RESET: dropped collections (users preservados)")

    await ensure_indexes(db)
    await seed_users(db)
    await seed_stations(db)
    await seed_wells(db)
    await seed_pipelines(db)
    await seed_wind_samples(db)
    await seed_detections_and_alerts(db)

    counts = {
        "users":        await db.users.count_documents({}),
        "stations":     await db.stations.count_documents({}),
        "wells":        await db.wells.count_documents({}),
        "pipelines":    await db.pipelines.count_documents({}),
        "detections":   await db.detections.count_documents({}),
        "alerts":       await db.alerts.count_documents({}),
        "wind_samples": await db.wind_samples.count_documents({}),
    }
    log.info("seed counts: %s", counts)
    return counts


# --------- CLI ---------

def _main() -> None:
    # Cargar .env al ejecutar como script
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="METAvision — seeder")
    parser.add_argument("--reset", action="store_true", help="Drop collections (except users) and reseed")
    args = parser.parse_args()

    async def _go():
        counts = await run_seed(reset=args.reset)
        print("SEED COUNTS:", counts)

    asyncio.run(_go())


if __name__ == "__main__":
    _main()
