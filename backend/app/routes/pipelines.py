"""Gasoductos."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import get_current_user
from app.db.mongo import get_db
from app.models.pipeline import Pipeline
from app.models.user import UserPublic
from app.routes._filters import parse_bbox

router = APIRouter(prefix="/pipelines", tags=["infrastructure"])


def _bbox_intersects(coords, bbox) -> bool:
    if bbox is None:
        return True
    minLng, minLat, maxLng, maxLat = bbox
    for lng, lat in coords:
        if minLng <= lng <= maxLng and minLat <= lat <= maxLat:
            return True
    return False


@router.get("", response_model=List[Pipeline])
async def list_pipelines(
    bbox: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    _user: UserPublic = Depends(get_current_user),
) -> List[Pipeline]:
    db = get_db()
    q: dict = {}
    if status: q["status"] = status
    bb = parse_bbox(bbox)
    docs = await db.pipelines.find(q, {"_id": 0}).sort("name", 1).to_list(100)
    if bb is not None:
        docs = [d for d in docs if _bbox_intersects(d["coordinates"], bb)]
    return [Pipeline(**d) for d in docs]


@router.get("/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(
    pipeline_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> Pipeline:
    db = get_db()
    doc = await db.pipelines.find_one({"id": pipeline_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Pipeline not found")
    return Pipeline(**doc)
