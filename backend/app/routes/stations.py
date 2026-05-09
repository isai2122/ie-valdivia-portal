"""Rutas de estaciones (protegidas Fase 1)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import get_current_user
from app.db.mongo import get_db
from app.models.station import Station
from app.models.user import UserPublic

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=List[Station])
async def list_stations(
    department: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    _user: UserPublic = Depends(get_current_user),
) -> List[Station]:
    db = get_db()
    q: dict = {}
    if department: q["department"] = department
    if risk_level: q["risk_level"] = risk_level
    if status:     q["status"] = status
    docs = await db.stations.find(q, {"_id": 0}).sort("name", 1).to_list(200)
    return [Station(**d) for d in docs]


@router.get("/{station_id}", response_model=Station)
async def get_station(
    station_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> Station:
    db = get_db()
    doc = await db.stations.find_one({"id": station_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Station not found")
    return Station(**doc)
