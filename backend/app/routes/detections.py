"""Detections CRUD y listados con filtros."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth.deps import get_current_user, require_roles
from app.db.mongo import get_db
from app.models.detection import Detection, DetectionCreate, DetectionPatch
from app.models.user import UserPublic
from app.routes._filters import bbox_mongo_filter, parse_bbox, parse_iso

router = APIRouter(prefix="/detections", tags=["detections"])


@router.get("", response_model=List[Detection])
async def list_detections(
    response: Response,
    bbox: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _user: UserPublic = Depends(get_current_user),
) -> List[Detection]:
    db = get_db()
    q: dict = {}
    q.update(bbox_mongo_filter(parse_bbox(bbox)))
    s = parse_iso(start_date, "start_date")
    e = parse_iso(end_date, "end_date")
    if s or e:
        rng: dict = {}
        if s: rng["$gte"] = s
        if e: rng["$lte"] = e
        q["detected_at"] = rng
    if severity: q["severity"] = severity
    if status:   q["status"] = status
    if min_confidence is not None: q["confidence"] = {"$gte": min_confidence}

    total = await db.detections.count_documents(q)
    response.headers["X-Total-Count"] = str(total)
    cursor = (
        db.detections.find(q, {"_id": 0})
        .sort("detected_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return [Detection(**d) async for d in cursor]


@router.get("/{det_id}", response_model=Detection)
async def get_detection(
    det_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> Detection:
    db = get_db()
    doc = await db.detections.find_one({"id": det_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Detection not found")
    return Detection(**doc)


@router.patch("/{det_id}", response_model=Detection)
async def patch_detection(
    det_id: str,
    payload: DetectionPatch,
    user: UserPublic = Depends(require_roles("admin", "analyst")),
) -> Detection:
    db = get_db()
    update: dict = {}
    if payload.status is not None: update["status"] = payload.status
    if payload.notes  is not None: update["notes"] = payload.notes
    if not update:
        raise HTTPException(400, "Nothing to update")
    update["reviewer_id"] = user.id
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.detections.update_one({"id": det_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "Detection not found")
    doc = await db.detections.find_one({"id": det_id}, {"_id": 0})
    return Detection(**doc)


@router.post("", response_model=Detection, status_code=201)
async def create_detection(
    payload: DetectionCreate,
    _user: UserPublic = Depends(require_roles("admin")),
) -> Detection:
    db = get_db()
    det = Detection(id=f"det-{uuid.uuid4().hex[:10]}", status="new",
                    **payload.model_dump())
    await db.detections.insert_one(det.model_dump())
    return det
