"""Alertas."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth.deps import get_current_user, require_roles
from app.db.mongo import get_db
from app.models.alert import Alert
from app.models.user import UserPublic
from app.routes._filters import parse_iso

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=List[Alert])
async def list_alerts(
    response: Response,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _user: UserPublic = Depends(get_current_user),
) -> List[Alert]:
    db = get_db()
    q: dict = {}
    s = parse_iso(start_date, "start_date")
    e = parse_iso(end_date, "end_date")
    if s or e:
        rng: dict = {}
        if s: rng["$gte"] = s
        if e: rng["$lte"] = e
        q["created_at"] = rng
    if severity is not None: q["severity"] = severity
    if acknowledged is not None: q["acknowledged"] = acknowledged

    total = await db.alerts.count_documents(q)
    response.headers["X-Total-Count"] = str(total)
    cursor = db.alerts.find(q, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit)
    return [Alert(**d) async for d in cursor]


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: str,
    _user: UserPublic = Depends(get_current_user),
) -> Alert:
    db = get_db()
    doc = await db.alerts.find_one({"id": alert_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Alert not found")
    return Alert(**doc)


@router.post("/{alert_id}/ack", response_model=Alert)
async def ack_alert(
    alert_id: str,
    user: UserPublic = Depends(require_roles("admin", "analyst")),
) -> Alert:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    res = await db.alerts.update_one(
        {"id": alert_id},
        {"$set": {
            "acknowledged": True,
            "acknowledged_by": user.email,
            "acknowledged_at": now,
        }},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Alert not found")
    doc = await db.alerts.find_one({"id": alert_id}, {"_id": 0})
    return Alert(**doc)
