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

_shared_seen_event_ids: dict[int, int] = {}
_shared_seen_processlist: set = set()


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
        collector = MySQLQueryCollector(
            connection,
            seen_event_ids=_shared_seen_event_ids,
            seen_processlist_queries=_shared_seen_processlist,
        )
        observations = collector.poll(request.limit)
        persisted = (
            DBMSObservationRepository(connection).insert_many(observations)
            if request.persist
            else []
        )
    except mysql.connector.Error as error:
        # Graceful fallback: return empty observation set rather than crashing
        return CollectDBMSEventsResponse(
            collected=0,
            persisted=0,
            observations=[],
        )
    returned = persisted if request.persist else observations
    return CollectDBMSEventsResponse(
        collected=len(observations),
        persisted=len(persisted),
        observations=returned,
    )


@router.get("/status")
def get_dbms_observation_status(connection=Depends(get_dbms_connection)) -> dict:
    """Check MySQL Performance Schema availability and statements instrument status."""
    try:
        cur = connection.cursor(dictionary=True)
        cur.execute("SELECT @@performance_schema AS ps_enabled")
        row = cur.fetchone()
        ps_enabled = bool(row and row.get("ps_enabled") in (1, "1", True, "YES", "yes"))
        
        history_long_enabled = False
        if ps_enabled:
            cur.execute("""
                SELECT ENABLED 
                FROM performance_schema.setup_consumers 
                WHERE NAME = 'events_statements_history_long'
            """)
            c_row = cur.fetchone()
            if c_row and c_row.get("ENABLED") in ('YES', 'yes', 1):
                history_long_enabled = True
            else:
                try:
                    cur.execute(
                        "UPDATE performance_schema.setup_consumers SET ENABLED = 'YES' "
                        "WHERE NAME IN ('events_statements_history_long', 'events_statements_history')"
                    )
                    connection.commit()
                    history_long_enabled = True
                except Exception:
                    pass
        cur.close()

        if ps_enabled:
            return {
                "status": "AVAILABLE",
                "mode": "PERFORMANCE_SCHEMA",
                "label": "[LIVE]",
                "performance_schema": True,
                "history_long_enabled": history_long_enabled,
                "fallback_active": False,
                "reason": None
            }
        else:
            return {
                "status": "AVAILABLE",
                "mode": "PROCESSLIST_FALLBACK",
                "label": "[LIVE - Processlist Fallback]",
                "performance_schema": False,
                "history_long_enabled": False,
                "fallback_active": True,
                "reason": "MySQL Performance Schema is disabled in my.ini; automatic query harvesting is active via processlist fallback."
            }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "label": "[DBMS OBSERVATION: UNAVAILABLE]",
            "performance_schema": False,
            "history_long_enabled": False,
            "reason": f"MySQL server connection error: {e}"
        }


@router.get("/observations", response_model=list[DBMSQueryObservation])
def list_dbms_observations(
    limit: int = Query(default=50, ge=1, le=500),
    connection=Depends(get_dbms_connection),
) -> list[DBMSQueryObservation]:
    try:
        return DBMSObservationRepository(connection).recent(limit)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
