"""Normalized OS and DBMS event models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class OSEventType(str, Enum):
    """Event types accepted by both the process and filesystem collectors."""

    # Process lifecycle events
    PROCESS_CREATED = "process_created"
    PROCESS_TERMINATED = "process_terminated"

    # Filesystem events — PID is always null for these (kernel-level auditing
    # is out of MVP scope, so file-to-PID mapping is intentionally deferred).
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_RENAMED = "file_renamed"
    FILE_DELETED = "file_deleted"
    DIR_CREATED = "dir_created"
    DIR_DELETED = "dir_deleted"

    # Resource snapshot events
    RESOURCE_SAMPLE = "resource_sample"


class OSEvent(BaseModel):
    """A single OS *process* event as reported by the collector.

    This model covers process_created and process_terminated events only.
    Filesystem events (which have pid=null by OS contract) use
    OSFilesystemEvent below and are accepted at a separate endpoint.
    """

    # ---- Fields from the OS Live Reality Mode contract ----

    # Collector-assigned UUID for this event (replaces the old integer id).
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        min_length=1,
        description="Collector-assigned UUID for this event.",
    )
    source: Literal["OS"] = Field(
        default="OS",
        description="Always 'OS' for events emitted by the OS collector.",
    )
    timestamp: datetime = Field(
        ..., description="When the event occurred (ISO 8601, timezone-aware preferred)."
    )
    event_type: OSEventType = Field(..., description="Kind of OS event.")
    operation: str | None = Field(
        default=None,
        description="High-level operation name, if the collector provides one.",
    )
    pid: int = Field(..., gt=0, description="Process ID. Must be a positive integer.")
    ppid: int = Field(..., ge=0, description="Parent process ID. 0 is valid (e.g. init).")
    process_name: str | None = Field(
        default=None,
        description="Executable name (basename), if known.",
    )
    user: str = Field(..., min_length=1, description="OS user that owns the process.")
    file_path: str | None = Field(
        default=None,
        description="Executable path, if known. The collector sends null when unavailable.",
    )
    resource_info: dict[str, Any] | None = Field(
        default=None,
        description="CPU/memory snapshot attached by the resource collector, if present.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Freeform key-value metadata emitted by the collector.",
    )
    host_id: str = Field(
        default="localhost",
        min_length=1,
        description="Stable identifier for the host that generated this event.",
    )
    # Collector-reported evidence completeness, e.g. '4/5'.  This is a count
    # of satisfied deterministic checks, not a probability.
    evidence_completeness: str | None = Field(
        default=None,
        description="Collector-assessed evidence completeness (e.g. '4/5').",
    )
    capture_latency_sec: float | None = Field(
        default=None,
        ge=0,
        description="Time between the OS event and when it was captured by the collector.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_process_event_type(cls, value: Any) -> Any:
        if cls is OSEvent and value not in (OSEventType.PROCESS_CREATED, OSEventType.PROCESS_TERMINATED, OSEventType.RESOURCE_SAMPLE):
            raise ValueError("Filesystem event types are not accepted at the process events endpoint")
        return value

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


class OSFilesystemEvent(BaseModel):
    """A filesystem event from the OS collector.

    Filesystem events intentionally carry ``pid=None``.  Tracing a file
    operation back to the originating PID requires kernel-level auditing,
    which is out of MVP scope.  Callers must not substitute a fake PID;
    the correlation engine uses time-window and file_path context instead.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        min_length=1,
        description="Collector-assigned UUID.",
    )
    source: Literal["OS"] = Field(default="OS")
    timestamp: datetime = Field(..., description="When the filesystem event occurred.")
    event_type: OSEventType = Field(
        ...,
        description="Kind of filesystem event (file_created, file_modified, etc.).",
    )
    operation: str | None = Field(default=None)
    # pid is intentionally Optional — the OS contract specifies null for all
    # filesystem events.  Do not set this to a fake value.
    pid: int | None = Field(
        default=None,
        description="Always null for filesystem events per the OS contract.",
    )
    file_path: str | None = Field(
        default=None,
        description="Path of the file or directory involved in the event.",
    )
    metadata: dict[str, Any] | None = Field(default=None)
    host_id: str = Field(
        default="localhost",
        min_length=1,
        description="Stable identifier for the host that generated this event.",
    )
    evidence_completeness: str | None = Field(default=None)
    capture_latency_sec: float | None = Field(default=None, ge=0)


class StoredOSEvent(OSEvent):
    """A process OS event as held in the service layer, with server-assigned metadata."""

    # Existing database seed data also contains file_* events. They are
    # returned as stored historical strings without widening the current
    # process-ingestion contract above.
    event_type: str
    id: int = Field(..., description="Server-assigned sequential ID.")
    received_at: datetime = Field(..., description="When the backend accepted the event.")


class StoredOSFilesystemEvent(OSFilesystemEvent):
    """A filesystem event as held in the service layer, with server-assigned metadata."""

    event_type: str
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
