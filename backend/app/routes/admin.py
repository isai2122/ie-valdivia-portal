"""Endpoint de admin (solo role=admin)."""
from typing import List

from fastapi import APIRouter, Depends

from app.auth.deps import require_roles
from app.db.mongo import get_db
from app.models.user import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserPublic])
async def list_users(_user: UserPublic = Depends(require_roles("admin"))) -> List[UserPublic]:
    """Lista los usuarios del sistema (solo admin). Nunca devuelve password_hash."""
    cursor = get_db().users.find(
        {}, {"_id": 0, "password_hash": 0}
    ).sort("email", 1)
    return [UserPublic(**d) async for d in cursor]
