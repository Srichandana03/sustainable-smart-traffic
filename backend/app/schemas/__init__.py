import datetime as dt
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AnalysisOut(BaseModel):
    id: int
    video_id: int
    status: str
    location: str
    latitude: float | None = None
    longitude: float | None = None
    filename: str
    detector_backend: str | None = None
    avg_vehicles: float | None = None
    max_vehicles: int | None = None
    congestion_level: str | None = None
    congestion_confidence: float | None = None
    co2_kg_per_hour: float | None = None
    details: dict[str, Any] | None = None
    error: str | None = None
    created_at: dt.datetime


class HotspotOut(BaseModel):
    rank: int
    location: str
    latitude: float | None
    longitude: float | None
    samples: int
    high_frequency: float
    severity: float
    avg_co2_kg_per_hour: float
    score: float


class ForecastPoint(BaseModel):
    time: str
    score: float
    level: str
    method: str


class SummaryOut(BaseModel):
    total_analyses: int
    locations: int
    level_distribution: dict[str, int]
    total_co2_kg_per_hour: float
    avg_vehicles: float
    model_trained: bool
    detector_backend: str
    carbon_limit_kg_per_hour: float
    within_limit: int
    over_limit: int
    pct_within_limit: float
