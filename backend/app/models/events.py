"""Normalized event models emitted by DBMS features."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class DBMSEvent(BaseModel):
    """Stable representation of one DBMS query execution event.

    The event contains the identifiers and query metadata needed to identify
    the same execution later.  ``timestamp`` is stored as a naive UTC
    ``datetime`` because that is the representation used by MySQL DATETIME.
    """

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
