"""DBMS event collection API."""

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, Query

from app.collectors.mysql_query_collector import MySQLQueryCollector
from app.config.database import get_connection
from app.models.dbms_observations import (
    CollectDBMSEventsRequest,
    CollectDBMSEventsResponse,
    DBMSQueryObservation,
)
from app.repositories.dbms_observation_repository import DBMSObservationRepository

router = APIRouter(prefix="/dbms-events", tags=["dbms-events"])


def get_dbms_connection():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.post("/collect", response_model=CollectDBMSEventsResponse)
def collect_dbms_events(
    request: CollectDBMSEventsRequest,
    connection=Depends(get_dbms_connection),
) -> CollectDBMSEventsResponse:
    try:
        observations = MySQLQueryCollector(connection).poll(request.limit)
        persisted = (
            DBMSObservationRepository(connection).insert_many(observations)
            if request.persist
            else []
        )
    except mysql.connector.Error as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "MySQL Performance Schema could not be queried. "
                f"Check performance_schema permissions and availability: {error}"
            ),
        ) from error
    returned = persisted if request.persist else observations
    return CollectDBMSEventsResponse(
        collected=len(observations),
        persisted=len(persisted),
        observations=returned,
    )


@router.get("/observations", response_model=list[DBMSQueryObservation])
def list_dbms_observations(
    limit: int = Query(default=50, ge=1, le=500),
    connection=Depends(get_dbms_connection),
) -> list[DBMSQueryObservation]:
    try:
        return DBMSObservationRepository(connection).recent(limit)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
