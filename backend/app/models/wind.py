"""Muestras de campo de viento en grilla."""
from typing import List

from pydantic import BaseModel, ConfigDict


class WindSample(BaseModel):
    """bbox=[minLng,minLat,maxLng,maxLat]. grid=[[lng,lat,speed_ms,dir_deg], ...] (100 pts)."""
    model_config = ConfigDict(extra="ignore")

    id: str
    sampled_at: str
    bbox: List[float]
    grid: List[List[float]]
