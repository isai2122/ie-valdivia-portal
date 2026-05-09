"""Detección de pluma de metano."""
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["info", "warning", "critical"]
Status = Literal["new", "reviewed", "dismissed"]


class Detection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    detected_at: str
    lat: float
    lng: float
    concentration_ppb: float
    plume_area_km2: float
    confidence: float
    source_station_id: Optional[str] = None
    source_well_id: Optional[str] = None
    wind_direction_deg: float = 0.0
    wind_speed_ms: float = 0.0
    severity: Severity = "info"
    status: Status = "new"
    reviewer_id: Optional[str] = None
    notes: Optional[str] = None
    sentinel_scene_id: Optional[str] = None
    plume_geojson: Optional[Dict[str, Any]] = None


class DetectionPatch(BaseModel):
    status: Optional[Status] = None
    notes: Optional[str] = None


class DetectionCreate(BaseModel):
    detected_at: str
    lat: float
    lng: float
    concentration_ppb: float
    plume_area_km2: float
    confidence: float = Field(ge=0.0, le=1.0)
    source_station_id: Optional[str] = None
    source_well_id: Optional[str] = None
    wind_direction_deg: float = 0.0
    wind_speed_ms: float = 0.0
    severity: Severity = "info"
    sentinel_scene_id: Optional[str] = None
    plume_geojson: Optional[Dict[str, Any]] = None
