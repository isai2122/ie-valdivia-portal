"""Dependencias FastAPI para auth."""
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.provider import JWTError, get_auth_provider
from app.models.user import UserPublic

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserPublic:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    provider = get_auth_provider()
    try:
        payload = provider.verify_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = await provider.get_user(uid)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    async def _dep(user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role in {sorted(allowed)}",
            )
        return user

    return _dep


def require_any_authenticated():
    # Alias semántico; devuelve el dep estándar.
    return get_current_user


def _ensure_roles(user: UserPublic, roles: Iterable[str]) -> None:
    if user.role not in set(roles):
        raise HTTPException(status_code=403, detail="Forbidden")
