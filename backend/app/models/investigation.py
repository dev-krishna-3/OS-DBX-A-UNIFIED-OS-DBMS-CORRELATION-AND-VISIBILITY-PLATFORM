"""Incident investigation and replay models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, PositiveInt

from app.models.deadlocks import IncidentRecord
from app.models.performance import PerformanceRecord


class InvestigationTimelineEntry(BaseModel):
    sequence: PositiveInt
    source: str
    source_id: int | None = None
    timestamp: datetime | None = None
    event_type: str
    description: str
    payload: dict[str, Any] = Field(default_factory=dict)


class IncidentInvestigation(BaseModel):
    incident: IncidentRecord
    trace: dict[str, Any] | None = None
    timeline: list[InvestigationTimelineEntry] = Field(default_factory=list)
    performance: list[PerformanceRecord] = Field(default_factory=list)


class IncidentReplay(BaseModel):
    replay_id: PositiveInt
    incident_id: PositiveInt
    replayed_at: datetime
    outcome: str
    steps: list[InvestigationTimelineEntry]
    summary: str
