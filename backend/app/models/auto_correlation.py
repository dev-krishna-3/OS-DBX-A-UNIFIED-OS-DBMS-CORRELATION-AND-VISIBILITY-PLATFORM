"""Models for automatic DBMS-to-OS correlation."""

from pydantic import BaseModel, Field, PositiveInt

from app.models.correlation import CorrelationResult


class AutoCorrelationRequest(BaseModel):
    observation_id: PositiveInt
    window_ms: int = Field(default=5000, ge=1, le=60000)
    persist: bool = True


class AutoCorrelationResponse(BaseModel):
    observation_id: PositiveInt
    matched_query_id: PositiveInt | None = None
    matched_os_event_ids: list[PositiveInt] = Field(default_factory=list)
    result: CorrelationResult | None = None
    reason: str | None = None
