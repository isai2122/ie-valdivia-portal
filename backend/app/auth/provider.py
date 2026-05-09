"""Abstracción de proveedor de autenticación.

El selector se controla por la variable de entorno AUTH_PROVIDER:
  - "local"    -> LocalJWTAuthProvider (por defecto)
  - "firebase" -> FirebaseAuthProvider (stub, pendiente)

Para cambiar de proveedor en el futuro basta con:
  1. Setear AUTH_PROVIDER=firebase en backend/.env
  2. Setear FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_JSON,
     FIREBASE_WEB_CONFIG en backend/.env
  3. Implementar FirebaseAuthProvider (reemplazar NotImplementedError)
No hace falta tocar rutas ni deps: éstas sólo consumen la interfaz.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    verify_password,
)
from app.db.mongo import get_db
from app.models.user import UserInDB, UserPublic


class AuthProvider(ABC):
    """Contrato mínimo. Cualquier provider debe cumplirlo."""

    @abstractmethod
    async def authenticate(self, email: str, password: str) -> Optional[UserPublic]:
        ...

    @abstractmethod
    async def issue_token(self, user: UserPublic) -> str:
        ...

    @abstractmethod
    def verify_token(self, token: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def get_user(self, uid: str) -> Optional[UserPublic]:
        ...


class LocalJWTAuthProvider(AuthProvider):
    """Auth local: bcrypt contra Mongo + JWT HS256 firmado con JWT_SECRET."""

    async def authenticate(self, email: str, password: str) -> Optional[UserPublic]:
        db = get_db()
        doc = await db.users.find_one(
            {"email": email.lower().strip()}, {"_id": 0}
        )
        if not doc or not doc.get("active", True):
            return None
        user = UserInDB(**doc)
        if not verify_password(password, user.password_hash):
            return None
        return user.to_public()

    async def issue_token(self, user: UserPublic) -> str:
        return create_access_token(sub=user.id, email=user.email, role=user.role)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Devuelve el payload o lanza jwt.PyJWTError."""
        return decode_token(token)

    async def get_user(self, uid: str) -> Optional[UserPublic]:
        db = get_db()
        doc = await db.users.find_one({"id": uid}, {"_id": 0})
        if not doc:
            return None
        return UserInDB(**doc).to_public()


class FirebaseAuthProvider(AuthProvider):
    """Stub. Pendiente de implementación.

    Variables de entorno esperadas cuando se implemente:
      - FIREBASE_PROJECT_ID
      - FIREBASE_CREDENTIALS_JSON   (json service account, base64 o ruta)
      - FIREBASE_WEB_CONFIG         (json con apiKey/authDomain/etc. para el SDK web)
    Implementará verificación de ID tokens de Firebase con firebase-admin.
    """

    def _not_impl(self) -> None:  # pragma: no cover - stub
        raise NotImplementedError(
            "FirebaseAuthProvider aún no está implementado. "
            "Setear AUTH_PROVIDER=local o implementar este provider "
            "con firebase-admin y las env vars FIREBASE_PROJECT_ID, "
            "FIREBASE_CREDENTIALS_JSON, FIREBASE_WEB_CONFIG."
        )

    async def authenticate(self, email: str, password: str) -> Optional[UserPublic]:  # noqa: ARG002
        self._not_impl()

    async def issue_token(self, user: UserPublic) -> str:  # noqa: ARG002
        self._not_impl()

    def verify_token(self, token: str) -> Dict[str, Any]:  # noqa: ARG002
        self._not_impl()

    async def get_user(self, uid: str) -> Optional[UserPublic]:  # noqa: ARG002
        self._not_impl()


_provider: AuthProvider | None = None


def get_auth_provider() -> AuthProvider:
    """Singleton perezoso con fallback a local si el selector es inválido."""
    global _provider
    if _provider is None:
        if settings.auth_provider == "firebase":
            _provider = FirebaseAuthProvider()
        else:
            _provider = LocalJWTAuthProvider()
    return _provider


# Re-exportado para que deps.py pueda atrapar errores JWT
JWTError = jwt.PyJWTError
