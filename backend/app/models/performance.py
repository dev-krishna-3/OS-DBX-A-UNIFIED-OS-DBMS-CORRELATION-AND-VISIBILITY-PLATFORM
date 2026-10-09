"""Performance measurement API models."""

from datetime import datetime

from pydantic import BaseModel, Field, PositiveInt


class PerformanceRecordCreate(BaseModel):
    trace_id: PositiveInt | None = None
    metric_name: str = Field(min_length=1, max_length=100)
    metric_value: float = Field(allow_inf_nan=False)
    recorded_at: datetime | None = None


class PerformanceRecord(PerformanceRecordCreate):
    record_id: PositiveInt
    recorded_at: datetime


class PerformanceCollectionRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)


class PerformanceCollectionResponse(BaseModel):
    collected: int
    records: list[PerformanceRecord]
