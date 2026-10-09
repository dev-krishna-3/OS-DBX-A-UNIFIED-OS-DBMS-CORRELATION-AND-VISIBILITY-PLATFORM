"""Saved what-if schedule and recovery analysis APIs."""

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.database import get_connection
from app.models.recovery import RecoveryResult
from app.models.schedules import ScheduleAnalysisResult
from app.models.what_if import (
    WhatIfRecoveryRequest,
    WhatIfScenario,
    WhatIfScheduleRequest,
)
from app.repositories.what_if_repository import WhatIfRepository
from app.services.recovery_service import RecoveryService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/what-if", tags=["what-if"])


def get_what_if_repository(connection=Depends(get_connection)):
    try:
        yield WhatIfRepository(connection)
    finally:
        connection.close()


@router.post("/schedules", response_model=WhatIfScenario, status_code=201)
def analyze_schedule_what_if(
    request: WhatIfScheduleRequest,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    result = ScheduleService().analyze(request.operations)
    return repository.create(
        "SCHEDULE",
        request.name,
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
    )


@router.post("/recovery", response_model=WhatIfScenario, status_code=201)
def analyze_recovery_what_if(
    request: WhatIfRecoveryRequest,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    result = RecoveryService().recover(request.initial_state, request.logs)
    return repository.create(
        "RECOVERY",
        request.name,
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
    )


@router.get("/scenarios", response_model=list[WhatIfScenario])
def list_what_if_scenarios(
    limit: int = Query(default=50, ge=1, le=500),
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> list[WhatIfScenario]:
    try:
        return repository.recent(limit)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/scenarios/{scenario_id}", response_model=WhatIfScenario)
def get_what_if_scenario(
    scenario_id: int,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    try:
        scenario = repository.get(scenario_id)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if scenario is None:
        raise HTTPException(status_code=404, detail="What-if scenario not found")
    return scenario
