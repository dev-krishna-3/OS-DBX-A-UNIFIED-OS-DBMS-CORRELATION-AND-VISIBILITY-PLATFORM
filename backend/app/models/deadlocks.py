"""Request and response models for wait-for graph analysis."""

from datetime import datetime

from typing import Any
from pydantic import BaseModel, Field, PositiveInt, field_validator, model_validator

from app.models.locks import LockStatus, LockType


class LockSnapshot(BaseModel):
    transaction_id: PositiveInt
    data_item: str = Field(min_length=1, max_length=255)
    lock_type: LockType = Field(default=LockType.EXCLUSIVE)
    status: LockStatus = Field(default=LockStatus.HELD)

    @model_validator(mode="before")
    @classmethod
    def _map_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "lock_type" not in data and "lock_mode" in data:
                data["lock_type"] = data["lock_mode"]
        return data

    @field_validator("lock_type", mode="before")
    @classmethod
    def _coerce_lock_type(cls, value: Any) -> LockType:
        if isinstance(value, LockType):
            return value
        if isinstance(value, str):
            s = value.strip().upper()
            if s in ("SHARED", "S", "READ"):
                return LockType.SHARED
            if s in ("EXCLUSIVE", "X", "WRITE"):
                return LockType.EXCLUSIVE
        return value


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
    fingerprint_hash: str | None = None
