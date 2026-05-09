"""Pozos petroleros/gaseros."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth.deps import get_current_user
from app.db.mongo import get_db
from app.models.user import UserPublic
from app.models.well import Well
from app.routes._filters import bbox_mongo_filter, parse_bbox

router = APIRouter(prefix="/wells", tags=["infrastructure"])


@router.get("", response_model=List[Well])
async def list_wells(
    response: Response,
    bbox: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None, alias="type"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _user: UserPublic = Depends(get_current_user),
) -> List[Well]:
    db = get_db()
    q: dict = {}
    q.update(bbox_mongo_filter(parse_bbox(bbox)))
    if status: q["status"] = status
    if type:   q["type"] = type

    total = await db.wells.count_documents(q)
    response.headers["X-Total-Count"] = str(total)
    cursor = db.wells.find(q, {"_id": 0}).sort("name", 1).skip(offset).limit(limit)
    return [Well(**d) async for d in cursor]


@router.get("/{well_id}", response_model=Well)
async def get_well(
    well_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> Well:
    db = get_db()
    doc = await db.wells.find_one({"id": well_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Well not found")
    return Well(**doc)
