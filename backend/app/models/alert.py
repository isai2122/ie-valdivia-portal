"""Alertas derivadas de detecciones."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

Severity = Literal["info", "warning", "critical"]


class Alert(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    detection_id: str
    created_at: str
    severity: Severity
    title: str
    message: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
