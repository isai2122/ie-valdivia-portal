"""Modelo Pydantic para estaciones de compresión (extendido Fase 1)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict

RiskLevel = Literal["low", "medium", "high"]


class Station(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    municipality: str
    department: str
    lat: float
    lng: float
    operator: str
    type: str = "compression_station"
    status: str = "active"
    # Fase 1
    capacity_mmscfd: float = 0.0
    installation_year: int = 2000
    risk_level: RiskLevel = "medium"
