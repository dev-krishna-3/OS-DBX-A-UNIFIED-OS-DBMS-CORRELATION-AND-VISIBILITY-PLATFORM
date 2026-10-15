"""Saved what-if schedule and recovery scenario models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, PositiveInt

from app.models.recovery import RecoveryLogEntry
from app.models.schedules import ScheduleOperation


class WhatIfScheduleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    operations: list[ScheduleOperation] = Field(default_factory=list)


class WhatIfRecoveryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    initial_state: dict[str, str] = Field(default_factory=dict)
    logs: list[RecoveryLogEntry] = Field(default_factory=list)


class WhatIfOSRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scenario_type: Literal[
        "CPU_LOAD",
        "PROCESS_LIFECYCLE",
        "MEMORY_PRESSURE",
        "FILESYSTEM_ACTIVITY",
        "DISK_IO",
        "SCHEDULING_POLICY",
        "RESOURCE_CONTENTION"
    ]
    parameters: dict[str, Any] = Field(default_factory=dict)


class WhatIfScenario(BaseModel):
    scenario_id: PositiveInt
    analysis_type: str
    name: str
    input_data: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime
