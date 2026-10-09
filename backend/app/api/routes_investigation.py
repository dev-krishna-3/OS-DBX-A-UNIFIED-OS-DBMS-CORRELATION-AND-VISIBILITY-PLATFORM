"""Incident investigation and replay APIs."""

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException

from app.config.database import get_connection
from app.models.investigation import IncidentInvestigation, IncidentReplay
from app.repositories.investigation_repository import (
    IncidentNotFoundError,
    InvestigationRepository,
    ReplayUnavailableError,
)

router = APIRouter(prefix="/incidents", tags=["investigation"])


def get_investigation_repository(connection=Depends(get_connection)):
    try:
        yield InvestigationRepository(connection)
    finally:
        connection.close()


@router.get("/{incident_id}/investigation", response_model=IncidentInvestigation)
def investigate_incident(
    incident_id: int,
    repository: InvestigationRepository = Depends(get_investigation_repository),
) -> IncidentInvestigation:
    try:
        return repository.investigate(incident_id)
    except IncidentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/{incident_id}/replay", response_model=IncidentReplay)
def replay_incident(
    incident_id: int,
    repository: InvestigationRepository = Depends(get_investigation_repository),
) -> IncidentReplay:
    try:
        investigation = repository.investigate(incident_id)
        return repository.save_replay(investigation)
    except IncidentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
    except ReplayUnavailableError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
