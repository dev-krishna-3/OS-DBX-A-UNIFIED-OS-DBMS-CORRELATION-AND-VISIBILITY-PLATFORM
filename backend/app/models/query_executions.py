"""Models for DBMS query execution events."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class DBMSEventType(str, Enum):
    QUERY_EXECUTION = "QUERY_EXECUTION"


class QueryExecutionRequest(BaseModel):
    """Validated data supplied when a query has finished executing."""

    transaction_id: int = Field(..., gt=0)
    pid: int = Field(..., gt=0)
    query_type: str = Field(..., min_length=1, max_length=50)
    query_text: str = Field(..., min_length=1)
    execution_time_ms: float = Field(..., ge=0)
    rows_affected: int = Field(..., ge=0)
    status: str = Field(..., min_length=1, max_length=50)

    @field_validator("query_type", "query_text", "status")
    @classmethod
    def value_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class DBMSEvent(QueryExecutionRequest):
    """A timestamped DBMS event ready for persistence."""

    event_type: DBMSEventType = DBMSEventType.QUERY_EXECUTION
    timestamp: datetime


class QueryExecutionRecord(DBMSEvent):
    """A persisted query execution with its database-generated ID."""

    query_id: int
