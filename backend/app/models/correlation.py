"""Pydantic models for deterministic cross-layer correlation."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from app.models.correlation_classification import (
    CorrelationClassification,
    EvidenceScore,
)


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    """Use UTC-naive datetimes, which match the existing MySQL DATETIME use."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _reject_blank(value: str) -> str:
    """Reject empty or whitespace-only labels without changing valid text."""

    if not value.strip():
        raise ValueError("value must not be blank")
    return value


class CorrelationInput(BaseModel):
    """One normalized event that can participate in a correlation attempt.

    Transaction and query IDs are optional here on purpose.  An input may be
    incomplete, but the service will not claim causation until both IDs are
    present and consistent across the candidate events.

    PID recycling note: PIDs are reused by the OS.  Provide
    ``process_start_time`` and ``process_stop_time`` when known so the
    correlation service can guard against stale PID matches.

    Null PID note: filesystem events carry ``pid=None`` by OS contract.
    The service uses time-window and ``file_path`` context for these.
    """

    model_config = ConfigDict(extra="forbid")

    # Collector-assigned UUID or sequential ID.
    os_event_id: str | int = Field(...)
    # pid is Optional to support filesystem events (which have pid=None).
    pid: int | None = Field(default=None, gt=0)
    transaction_id: PositiveInt | None = None
    query_id: PositiveInt | None = None
    timestamp: datetime
    event_type: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)

    @field_validator("os_event_id", mode="before")
    @classmethod
    def _validate_os_event_id(cls, value: Any) -> str | int:
        if isinstance(value, int):
            if value <= 0:
                raise ValueError("os_event_id must be a positive integer or non-empty string")
            return value
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("os_event_id must not be blank")
            return value
        raise ValueError("os_event_id must be a string or positive integer")

    # --- PID-recycling guard fields ---
    # When provided, the correlation service will verify that `timestamp`
    # falls strictly within [process_start_time, process_stop_time].
    process_start_time: datetime | None = None
    process_stop_time: datetime | None = None

    # --- Cross-host and evidence fields ---
    host_id: str | None = Field(
        default=None,
        description="Host that produced this event; must match across all candidates.",
    )
    # Forwarded from the OS collector (e.g. '4/5').
    evidence_completeness: str | None = Field(
        default=None,
        description="Collector-reported evidence completeness count (e.g. '4/5').",
    )
    file_path: str | None = Field(
        default=None,
        description="File path context; used for null-PID filesystem correlation.",
    )

    _validate_text = field_validator("event_type", "source")(_reject_blank)
    _validate_timestamp = field_validator("timestamp")(_normalize_timestamp)


class CrossLayerTrace(BaseModel):
    """A trace joining one process (or filesystem path), transaction, and query context.

    ``pid`` is Optional because filesystem-only traces have no process PID
    per the OS contract.  When ``pid`` is None, ``file_path`` should be set.
    """

    model_config = ConfigDict(extra="forbid")

    # The database assigns this value when a trace is persisted.
    trace_id: PositiveInt | None = None
    # None for filesystem-only traces (pid=null by OS contract).
    pid: int | None = Field(default=None, gt=0)
    transaction_id: PositiveInt | None = None
    host_id: str | None = None
    status: str = Field(min_length=1, max_length=50)
    started_at: datetime
    ended_at: datetime | None = None
    summary: str | None = None

    _validate_status = field_validator("status")(_reject_blank)
    _validate_started_at = field_validator("started_at")(_normalize_timestamp)
    _validate_ended_at = field_validator("ended_at")(_normalize_timestamp)


class EventCorrelation(BaseModel):
    """One ordered relationship between an OS event and a DBMS query."""

    model_config = ConfigDict(extra="forbid")

    # Correlation and trace IDs are assigned by persistence later.
    correlation_id: PositiveInt | None = None
    trace_id: PositiveInt | None = None
    os_event_id: str | int = Field(...)
    db_event_id: PositiveInt | None = None

    @field_validator("os_event_id", mode="before")
    @classmethod
    def _coerce_os_event_id(cls, value: Any) -> str | int:
        if isinstance(value, int):
            if value <= 0:
                raise ValueError("os_event_id must be a positive integer or non-empty string")
            return value
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("os_event_id must not be blank")
            return value
        raise ValueError("os_event_id must be a string or positive integer")
    # Optional to support filesystem-only traces where there is no DBMS query.
    query_id: PositiveInt | None = None
    correlation_method: str = Field(min_length=1, max_length=100)
    # Retained as nullable for compatibility with the existing database/API
    # shape. Correlation is rule-based and does not calculate probabilities.
    confidence_score: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    sequence_order: PositiveInt

    _validate_method = field_validator("correlation_method")(_reject_blank)



class CorrelationResult(BaseModel):
    """Result of one deterministic correlation attempt."""

    model_config = ConfigDict(extra="forbid")

    trace: CrossLayerTrace | None = None
    correlations: list[EventCorrelation] = Field(default_factory=list)
    reason: str | None = None
    classification: CorrelationClassification = CorrelationClassification.NONE
    evidence_score: EvidenceScore | None = None
    evidence_summary: str | None = None
    # The OS collector's own evidence completeness count, forwarded verbatim
    # (e.g. "4/5").  Not a probability; do not treat it as one.
    os_evidence_completeness: str | None = Field(
        default=None,
        description=(
            "Collector-reported evidence completeness forwarded from the OS event "
            "(e.g. '4/5').  This counts deterministic checks, not a probability."
        ),
    )

    @property
    def causal_sequence(self) -> list[EventCorrelation]:
        """Return correlations in their deterministic causal order."""

        return self.correlations

    @property
    def is_correlated(self) -> bool:
        """Tell callers whether a causal claim was produced."""

        return self.trace is not None and bool(self.correlations)



class CorrelationRequest(BaseModel):
    """API request containing the normalized events to correlate."""

    model_config = ConfigDict(extra="forbid")

    events: list[CorrelationInput] = Field(min_length=1)


# Descriptive aliases keep the model easy to discover for callers using either
# the short domain name or the full cross-layer name.
NormalizedCorrelationInput = CorrelationInput
CrossLayerCorrelationInput = CorrelationInput
