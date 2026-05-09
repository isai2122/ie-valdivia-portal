"""Viento: devuelve la WindSample más cercana a `at` (ISO)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import get_current_user
from app.db.mongo import get_db
from app.models.user import UserPublic
from app.models.wind import WindSample

router = APIRouter(prefix="/wind", tags=["wind"])


@router.get("", response_model=WindSample)
async def get_wind(
    at: Optional[str] = Query(None, description="ISO datetime"),
    _user: UserPublic = Depends(get_current_user),
) -> WindSample:
    db = get_db()
    if at is None:
        at = datetime.now(timezone.utc).isoformat()
    try:
        target = datetime.fromisoformat(at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "at must be ISO datetime")

    # Pick closest by parsed datetime in Python (N ≤ 30, trivial).
    docs = await db.wind_samples.find({}, {"_id": 0}).to_list(60)
    if not docs:
        raise HTTPException(404, "No wind samples available")

    def _delta(d):
        try:
            t = datetime.fromisoformat(d["sampled_at"].replace("Z", "+00:00"))
        except Exception:
            return float("inf")
        return abs((t - target).total_seconds())

    best = min(docs, key=_delta)
    return WindSample(**best)
