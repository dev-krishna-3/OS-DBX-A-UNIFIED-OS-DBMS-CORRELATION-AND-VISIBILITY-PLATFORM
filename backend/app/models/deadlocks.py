"""Request and response models for wait-for graph analysis."""

from datetime import datetime

from pydantic import BaseModel, Field, PositiveInt

from app.models.locks import LockStatus, LockType


class LockSnapshot(BaseModel):
    transaction_id: PositiveInt
    data_item: str = Field(min_length=1, max_length=255)
    lock_type: LockType
    status: LockStatus


class DeadlockDetectionRequest(BaseModel):
    locks: list[LockSnapshot] = Field(default_factory=list)


class DeadlockDetectionResult(BaseModel):
    deadlock_detected: bool
    wait_for_graph: dict[str, list[int]]
    cycles: list[list[int]] = Field(default_factory=list)
    incident_id: PositiveInt | None = None


class IncidentRecord(BaseModel):
    incident_id: PositiveInt
    trace_id: PositiveInt | None = None
    incident_type: str
    description: str | None = None
    detected_at: datetime | None = None
    resolved: bool | None = None
