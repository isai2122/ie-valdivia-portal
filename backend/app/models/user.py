"""Modelos Pydantic v2 para User."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["admin", "analyst", "viewer"]


class UserPublic(BaseModel):
    """Lo que se expone al frontend (sin password_hash)."""
    model_config = ConfigDict(extra="ignore")

    id: str
    email: EmailStr
    name: str
    role: Role
    active: bool = True


class UserInDB(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: Role
    password_hash: str
    active: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_public(self) -> UserPublic:
        return UserPublic(
            id=self.id, email=self.email, name=self.name,
            role=self.role, active=self.active,
        )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
