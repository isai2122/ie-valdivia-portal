"""Gasoductos — GeoJSON LineString aproximado."""
from typing import List, Literal

from pydantic import BaseModel, ConfigDict

PipeStatus = Literal["active", "maintenance", "retired"]


class Pipeline(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    operator: str
    diameter_inches: float
    length_km: float
    coordinates: List[List[float]]  # [[lng,lat], ...]
    status: PipeStatus = "active"
    pressure_psi: float = 1000.0
