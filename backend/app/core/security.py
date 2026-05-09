"""Utilidades de hashing bcrypt + creación/verificación de JWT HS256."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(*, sub: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expires_hours),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> Dict[str, Any]:
    """Lanza jwt.PyJWTError en caso de problema."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
