"""Inference jobs — MOCK (demo-synthetic) hasta exportar ONNX real.

NOTA: Este runner NO ejecuta el modelo. Genera 1–3 detecciones sintéticas
verosímiles en el bbox Magdalena Medio y emite alertas por WebSocket. Pensado
para que el frontend pueda desarrollarse end-to-end mientras el modelo ONNX
se exporta en Fase posterior.
"""
import asyncio
import logging
import random
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.mongo import get_db
from app.models.alert import Alert
from app.models.detection import Detection
from app.models.inference import (InferenceJob, InferenceJobCreateResponse,
                                  InferenceMetrics, ModelInfo)
from app.models.user import UserPublic
from app.services.plume import make_plume_polygon
from app.ws.manager import manager

log = logging.getLogger("inference")

router = APIRouter(prefix="/inference", tags=["inference"])

STORAGE_ROOT = Path("/app/backend/storage/inference")
ALLOWED_EXT = {".nc", ".tif", ".tiff", ".nc4"}
DEMO_WARNING = (
    "Modelo ONNX no cargado. Se usará generador demo hasta que se exporte "
    "metano_srgan_elite.onnx"
)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def _run_demo_inference(job_id: str, created_by: str) -> None:
    """Background task. No es inferencia real."""
    db = get_db()
    try:
        await asyncio.sleep(random.uniform(3.0, 6.0))
        await db.inference_jobs.update_one({"id": job_id}, {"$set": {"status": "running"}})

        min_lng, min_lat, max_lng, max_lat = settings.mm_bbox
        n = random.randint(1, 3)
        rng = random.Random()
        det_ids: List[str] = []
        now = datetime.now(timezone.utc)

        for _ in range(n):
            lat = rng.uniform(min_lat + 0.3, max_lat - 0.3)
            lng = rng.uniform(min_lng + 0.3, max_lng - 0.3)
            ppb = rng.uniform(1800, 2600)
            area = rng.uniform(0.3, 4.0)
            conf = rng.uniform(0.7, 0.95)
            wind_dir = rng.uniform(30, 110)
            r = rng.random()
            severity = "critical" if r > 0.85 else ("warning" if r > 0.55 else "info")

            det = Detection(
                id=f"det-{uuid.uuid4().hex[:10]}",
                detected_at=_iso(now),
                lat=round(lat, 5), lng=round(lng, 5),
                concentration_ppb=round(ppb, 1),
                plume_area_km2=round(area, 2),
                confidence=round(conf, 3),
                wind_direction_deg=round(wind_dir, 1),
                wind_speed_ms=round(rng.uniform(1.5, 5.0), 2),
                severity=severity, status="new",
                sentinel_scene_id=f"DEMO_JOB_{job_id[:8]}",
                plume_geojson=make_plume_polygon(lat, lng, area, wind_dir, vertices=12),
            )
            await db.detections.insert_one(det.model_dump())
            det_ids.append(det.id)

            alert = Alert(
                id=f"alert-{uuid.uuid4().hex[:10]}",
                detection_id=det.id,
                created_at=_iso(datetime.now(timezone.utc)),
                severity=severity,
                title=f"[demo] Detección {round(ppb, 0)} ppb",
                message=f"Job {job_id[:8]} generó una pluma de {round(area,1)} km².",
            )
            await db.alerts.insert_one(alert.model_dump())

            await manager.broadcast({
                "type": "alert.created",
                "alert": alert.model_dump(),
                "detection": det.model_dump(),
                "source": "inference_job",
                "job_id": job_id,
            })

        await db.inference_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "done",
                "output_detection_ids": det_ids,
                "metrics": InferenceMetrics(psnr=32.19, ssim=0.89).model_dump(),
            }},
        )
        log.info("inference job %s done (%d detections)", job_id, len(det_ids))
    except Exception as exc:  # noqa: BLE001
        log.exception("inference job %s failed", job_id)
        await db.inference_jobs.update_one(
            {"id": job_id}, {"$set": {"status": "failed", "error": str(exc)}}
        )


@router.post("/jobs", response_model=InferenceJobCreateResponse)
async def create_job(
    file: UploadFile = File(...),
    user: UserPublic = Depends(require_roles("admin", "analyst")),
) -> InferenceJobCreateResponse:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            400,
            f"Extensión no soportada: {ext!r}. Permitidas: {sorted(ALLOWED_EXT)}",
        )

    job_id = f"job-{uuid.uuid4().hex[:10]}"
    job_dir = STORAGE_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / f"input{ext}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    now = datetime.now(timezone.utc)
    job = InferenceJob(
        id=job_id,
        created_at=_iso(now),
        status="queued",
        input_filename=file.filename or dest.name,
        output_detection_ids=[],
        metrics=InferenceMetrics(),
        created_by=user.email,
        runner="demo-synthetic",
    )
    await get_db().inference_jobs.insert_one(job.model_dump())

    asyncio.create_task(_run_demo_inference(job_id, user.email))
    log.info("inference job %s queued (file=%s user=%s)", job_id, file.filename, user.email)

    return InferenceJobCreateResponse(
        job_id=job_id, status="queued", runner="demo-synthetic", warning=DEMO_WARNING,
    )


@router.get("/jobs", response_model=List[InferenceJob])
async def list_jobs(
    limit: int = 50, offset: int = 0,
    _user: UserPublic = Depends(get_current_user),
) -> List[InferenceJob]:
    db = get_db()
    cursor = db.inference_jobs.find({}, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit)
    return [InferenceJob(**d) async for d in cursor]


@router.get("/jobs/{job_id}", response_model=InferenceJob)
async def get_job(
    job_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> InferenceJob:
    doc = await get_db().inference_jobs.find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Job not found")
    return InferenceJob(**doc)


# -------- Model info endpoint --------

model_router = APIRouter(prefix="/model", tags=["model"])


@model_router.get("/info", response_model=ModelInfo)
async def model_info(_user: UserPublic = Depends(get_current_user)) -> ModelInfo:
    return ModelInfo(
        name="MetanoSRGAN Elite v2.1",
        weights_file="best.pt",
        weights_loaded=False,
        onnx_loaded=False,
        onnx_path=None,
        psnr_reported=32.19,
        params=1_940_000,
        trained_at="synthetic_dataset_v1",
        notes="Fine-tuning con datos reales pendiente",
    )
