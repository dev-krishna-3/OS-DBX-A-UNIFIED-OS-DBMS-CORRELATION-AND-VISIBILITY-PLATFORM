"""Normalized OS and DBMS event models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class OSEventType(str, Enum):
    """Event types currently emitted by the OS collector."""

    PROCESS_CREATED = "process_created"
    PROCESS_TERMINATED = "process_terminated"


class OSEvent(BaseModel):
    """A single OS event as reported by the collector."""

    timestamp: datetime = Field(
        ..., description="When the event occurred (ISO 8601, timezone-aware preferred)."
    )
    pid: int = Field(..., gt=0, description="Process ID. Must be a positive integer.")
    ppid: int = Field(..., ge=0, description="Parent process ID. 0 is valid (e.g. init).")
    user: str = Field(..., min_length=1, description="OS user that owns the process.")
    event_type: OSEventType = Field(..., description="Kind of OS event.")
    file_path: str | None = Field(
        default=None,
        description="Executable path, if known. The collector sends null when unavailable.",
    )

    @field_validator("user")
    @classmethod
    def user_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("user must not be blank")
        return stripped

    @field_validator("file_path")
    @classmethod
    def blank_file_path_to_none(cls, value: str | None) -> str | None:
        if value is not None and value.strip() == "":
            return None
        return value


class StoredOSEvent(OSEvent):
    """An OS event as held in the service layer, with server-assigned metadata."""

    id: int = Field(..., description="Server-assigned sequential ID.")
    received_at: datetime = Field(..., description="When the backend accepted the event.")


class DBMSEvent(BaseModel):
    """Stable representation of one DBMS query execution event."""

    model_config = ConfigDict(extra="forbid")

    event_type: Literal["QUERY_EXECUTION"] = "QUERY_EXECUTION"
    query_id: PositiveInt | None = None
    transaction_id: PositiveInt
    pid: PositiveInt
    query_type: str = Field(min_length=1, max_length=50)
    query_text: str = Field(min_length=1)
    execution_time_ms: float = Field(ge=0, allow_inf_nan=False)
    rows_affected: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=50)
    timestamp: datetime

    @field_validator("query_type", "query_text", "status")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """Reject blank values without changing the original metadata."""

        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        """Convert timestamps to the UTC-naive form accepted by DATETIME."""

        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
