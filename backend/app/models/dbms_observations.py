"""Normalized observations collected from MySQL Performance Schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class DBMSQueryObservation(BaseModel):
    """One completed MySQL statement observed by the collector."""

    model_config = ConfigDict(extra="forbid")

    observation_id: PositiveInt | None = None
    source_thread_id: PositiveInt
    source_event_id: PositiveInt
    connection_id: PositiveInt | None = None
    processlist_user: str | None = None
    database_name: str | None = None
    query_type: str = Field(min_length=1, max_length=50)
    query_text: str = Field(min_length=1)
    execution_time_ms: float = Field(ge=0, allow_inf_nan=False)
    rows_affected: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=50)
    observed_at: datetime


class CollectDBMSEventsRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    persist: bool = True


class CollectDBMSEventsResponse(BaseModel):
    collected: int
    persisted: int
    observations: list[DBMSQueryObservation]
