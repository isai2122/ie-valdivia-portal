"""Reports — CSV implementado vía pandas. PDF diferido a Fase 5 (501)."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth.deps import get_current_user
from app.db.mongo import get_db
from app.models.stats import Report, ReportCreate
from app.models.user import UserPublic

router = APIRouter(prefix="/reports", tags=["reports"])

STORAGE_ROOT = Path(__file__).parent.parent.parent / "storage" / "reports"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def _iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


async def _build_detections_csv(report_id: str, filters: dict) -> Path:
    """Genera CSV con detecciones filtradas. Filtros reconocidos: severity, status, min_confidence."""
    db = get_db()
    q: dict = {}
    if filters.get("severity"):        q["severity"] = filters["severity"]
    if filters.get("status"):          q["status"] = filters["status"]
    if "min_confidence" in filters:
        q["confidence"] = {"$gte": float(filters["min_confidence"])}
    docs = await db.detections.find(q, {"_id": 0}).sort("detected_at", -1).to_list(5000)
    if docs:
        df = pd.DataFrame(docs)
        keep = [c for c in [
            "id", "detected_at", "lat", "lng", "concentration_ppb",
            "plume_area_km2", "confidence", "severity", "status",
            "source_station_id", "source_well_id", "wind_direction_deg",
            "wind_speed_ms", "sentinel_scene_id",
        ] if c in df.columns]
        df = df[keep]
    else:
        df = pd.DataFrame(columns=["id", "detected_at", "severity"])
    dest = STORAGE_ROOT / f"{report_id}.csv"
    df.to_csv(dest, index=False, encoding="utf-8")
    return dest


@router.post("", response_model=Report)
async def create_report(
    payload: ReportCreate,
    user: UserPublic = Depends(get_current_user),
) -> Report:
    if payload.format == "pdf":
        raise HTTPException(501, "PDF report generation is scheduled for phase 5 and is not implemented yet.")
    if payload.type != "detections":
        raise HTTPException(501, f"Report type '{payload.type}' not implemented yet. Only 'detections' is available in phase 1.")

    report_id = f"rep-{uuid.uuid4().hex[:10]}"
    # Generación sincrónica, CSV es pequeño.
    dest = await _build_detections_csv(report_id, payload.filters or {})
    doc = Report(
        id=report_id, type=payload.type, format=payload.format, status="done",
        created_at=_iso(), created_by=user.email, filters=payload.filters or {},
        download_url=f"/api/reports/{report_id}/download",
    ).model_dump()
    await get_db().reports.insert_one(doc)
    return Report(**doc)


@router.get("", response_model=List[Report])
async def list_reports(_user: UserPublic = Depends(get_current_user)) -> List[Report]:
    cursor = get_db().reports.find({}, {"_id": 0}).sort("created_at", -1).limit(100)
    return [Report(**d) async for d in cursor]


@router.get("/{report_id}", response_model=Report)
async def get_report(
    report_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> Report:
    doc = await get_db().reports.find_one({"id": report_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Report not found")
    return Report(**doc)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    _user: UserPublic = Depends(get_current_user),
):
    doc = await get_db().reports.find_one({"id": report_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Report not found")
    path = STORAGE_ROOT / f"{report_id}.csv"
    if not path.exists():
        raise HTTPException(410, "Report file missing")
    return FileResponse(
        path, media_type="text/csv",
        filename=f"metavision_detections_{report_id}.csv",
    )
