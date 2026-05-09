"""Pozos petroleros/gaseros."""
from typing import Literal

from pydantic import BaseModel, ConfigDict

WellType = Literal["gas", "oil", "dual"]
WellStatus = Literal["active", "suspended", "abandoned"]


class Well(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    operator: str
    lat: float
    lng: float
    type: WellType
    status: WellStatus
    department: str
    municipality: str
