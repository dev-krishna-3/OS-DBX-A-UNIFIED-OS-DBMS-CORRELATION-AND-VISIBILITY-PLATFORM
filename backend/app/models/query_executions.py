"""Request and response models for query execution tracking."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from app.models.events import DBMSEvent


class QueryExecutionRequest(BaseModel):
    """Data supplied when a query has finished executing."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: PositiveInt
    pid: PositiveInt
    query_type: str = Field(min_length=1, max_length=50)
    query_text: str = Field(min_length=1)
    execution_time_ms: float = Field(ge=0, allow_inf_nan=False)
    rows_affected: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=50)
    timestamp: datetime | None = None

    @field_validator("query_type", "query_text", "status")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class QueryExecutionRecord(DBMSEvent):
    """Persisted query execution event returned after insert."""

    query_id: PositiveInt


QueryExecutionResponse = QueryExecutionRecord
