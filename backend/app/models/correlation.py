"""Pydantic models for deterministic cross-layer correlation."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


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
    """

    model_config = ConfigDict(extra="forbid")

    os_event_id: PositiveInt
    pid: PositiveInt
    transaction_id: PositiveInt | None = None
    query_id: PositiveInt | None = None
    timestamp: datetime
    event_type: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)

    _validate_text = field_validator("event_type", "source")(_reject_blank)
    _validate_timestamp = field_validator("timestamp")(_normalize_timestamp)


class CrossLayerTrace(BaseModel):
    """A trace joining one process, transaction, and query context."""

    model_config = ConfigDict(extra="forbid")

    # The database assigns this value when a trace is persisted.
    trace_id: PositiveInt | None = None
    pid: PositiveInt
    transaction_id: PositiveInt
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
    os_event_id: PositiveInt
    db_event_id: PositiveInt | None = None
    query_id: PositiveInt
    correlation_method: str = Field(min_length=1, max_length=100)
    confidence_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    sequence_order: PositiveInt

    _validate_method = field_validator("correlation_method")(_reject_blank)


class CorrelationResult(BaseModel):
    """Result of one deterministic correlation attempt."""

    model_config = ConfigDict(extra="forbid")

    trace: CrossLayerTrace | None = None
    correlations: list[EventCorrelation] = Field(default_factory=list)
    reason: str | None = None

    @property
    def causal_sequence(self) -> list[EventCorrelation]:
        """Return correlations in their deterministic causal order."""

        return self.correlations

    @property
    def is_correlated(self) -> bool:
        """Tell callers whether a causal claim was produced."""

        return self.trace is not None and bool(self.correlations)


# Descriptive aliases keep the model easy to discover for callers using either
# the short domain name or the full cross-layer name.
NormalizedCorrelationInput = CorrelationInput
CrossLayerCorrelationInput = CorrelationInput
