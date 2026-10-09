"""Models for transaction locks."""

from datetime import datetime
from enum import Enum

from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


class LockType(str, Enum):
    SHARED = "S"
    EXCLUSIVE = "X"


class LockStatus(str, Enum):
    HELD = "HELD"
    WAITING = "WAITING"
    RELEASED = "RELEASED"


class LockRequest(BaseModel):
    transaction_id: int = Field(..., gt=0)
    data_item: str = Field(..., min_length=1, max_length=255)
    lock_type: LockType = Field(default=LockType.EXCLUSIVE)

    @model_validator(mode="before")
    @classmethod
    def _map_lock_mode(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "lock_type" not in data and "lock_mode" in data:
                data = dict(data)
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

    @field_validator("data_item")
    @classmethod
    def data_item_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("data_item must not be blank")
        return value


class LockRecord(BaseModel):
    lock_id: int
    transaction_id: int
    data_item: str
    lock_type: LockType
    status: LockStatus
    acquired_at: datetime | None = None
    released_at: datetime | None = None
