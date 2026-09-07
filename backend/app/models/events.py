"""
OS event model.

Validates events against the contract already produced by
`os_monitor/collector.py` (see os_monitor/README.md):

    {
        "timestamp": "2026-08-26T10:15:03.221+00:00",
        "pid": 4211,
        "ppid": 1,
        "user": "krishna",
        "event_type": "process_created",
        "file_path": "/usr/bin/python3"
    }

Only the two event types the collector currently emits are accepted.
New event types (e.g. filesystem events) should be added to
`OSEventType` when the collector starts producing them - do not
loosen validation to accept arbitrary strings.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


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
        # The collector sends null for unavailable paths, but guard against
        # an empty string slipping through too.
        if value is not None and value.strip() == "":
            return None
        return value


class StoredOSEvent(OSEvent):
    """An OS event as held in the service layer, with server-assigned metadata."""

    id: int = Field(..., description="Server-assigned sequential ID.")
    received_at: datetime = Field(..., description="When the backend accepted the event.")
