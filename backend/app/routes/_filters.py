"""Helpers de filtros comunes para las rutas."""
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, Query


def parse_bbox(bbox: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not bbox:
        return None
    try:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError
        return tuple(parts)  # type: ignore[return-value]
    except ValueError:
        raise HTTPException(400, detail="bbox must be 'minLng,minLat,maxLng,maxLat'")


def bbox_mongo_filter(bbox: Optional[Tuple[float, float, float, float]]) -> dict:
    if not bbox:
        return {}
    minLng, minLat, maxLng, maxLat = bbox
    return {
        "lat": {"$gte": minLat, "$lte": maxLat},
        "lng": {"$gte": minLng, "$lte": maxLng},
    }


def parse_iso(v: Optional[str], field: str) -> Optional[str]:
    if v is None:
        return None
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, detail=f"{field} must be ISO datetime")
    return v


def paging(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Tuple[int, int]:
    return limit, offset


def sort_list(docs: List[dict], key: str, reverse: bool = True) -> List[dict]:
    return sorted(docs, key=lambda d: d.get(key, ""), reverse=reverse)
