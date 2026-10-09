"""Response models for the self-contained FastAPI demonstration endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.correlation import CorrelationInput, CorrelationResult


class DemoCheck(BaseModel):
    """One assertion made by a demo run."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    passed: bool
    detail: str = Field(min_length=1)


class CorrelationDemoResponse(BaseModel):
    """Observable result of the no-database correlation demonstration."""

    model_config = ConfigDict(extra="forbid")

    demo: str = Field(min_length=1)
    status: Literal["PASS", "FAIL"]
    generated_at: datetime
    input_events: list[CorrelationInput]
    result: CorrelationResult
    checks: list[DemoCheck]
