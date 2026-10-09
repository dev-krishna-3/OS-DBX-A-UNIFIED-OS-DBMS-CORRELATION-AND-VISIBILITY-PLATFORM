"""Deadlock analysis API."""

from fastapi import APIRouter, Depends, Query

from app.config.database import get_connection
from app.models.deadlocks import (
    DeadlockDetectionRequest,
    DeadlockDetectionResult,
    IncidentRecord,
)
from app.repositories.deadlock_repository import DeadlockRepository
from app.services.deadlock_service import DeadlockService

router = APIRouter(prefix="/deadlocks", tags=["deadlocks"])


@router.post("/detect", response_model=DeadlockDetectionResult)
def detect_deadlock(request: DeadlockDetectionRequest) -> DeadlockDetectionResult:
    return DeadlockService().detect(request.locks)


def get_deadlock_repository(connection=Depends(get_connection)):
    try:
        yield DeadlockRepository(connection)
    finally:
        connection.close()


@router.post("/detect/live", response_model=DeadlockDetectionResult)
def detect_live_deadlock(
    repository: DeadlockRepository = Depends(get_deadlock_repository),
) -> DeadlockDetectionResult:
    result = DeadlockService().detect(repository.active_locks())
    if not result.deadlock_detected:
        return result
    incident_id = repository.record_deadlock(result.cycles, result.wait_for_graph)
    return result.model_copy(update={"incident_id": incident_id})


@router.get("/incidents", response_model=list[IncidentRecord])
def list_incidents(
    limit: int = Query(default=50, ge=1, le=500),
    repository: DeadlockRepository = Depends(get_deadlock_repository),
) -> list[IncidentRecord]:
    """List recent persisted incidents, including detected deadlocks."""

    return repository.recent_incidents(limit)
