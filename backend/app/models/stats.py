"""Modelos auxiliares: stats, reports."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class TimeseriesPoint(BaseModel):
    date: str
    count: int
    avg_ppb: float


class StatsOverview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_detections: int
    detections_last_24h: int
    active_alerts: int
    critical_alerts: int
    stations_count: int
    avg_ppb_last_7d: float
    detections_by_severity: Dict[str, int]
    detections_timeseries_30d: List[TimeseriesPoint]


ReportType = Literal["detections", "trends", "infrastructure"]
ReportFormat = Literal["pdf", "csv"]
ReportStatus = Literal["queued", "running", "done", "failed"]


class ReportCreate(BaseModel):
    type: ReportType
    format: ReportFormat
    filters: Dict = {}


class Report(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    type: ReportType
    format: ReportFormat
    status: ReportStatus
    created_at: str
    created_by: str
    filters: Dict = {}
    download_url: Optional[str] = None
    error: Optional[str] = None
