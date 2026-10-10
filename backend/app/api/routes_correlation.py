"""Cross-layer correlation API."""

from fastapi import APIRouter, Depends, HTTPException

from app.config.database import get_connection
from app.models.auto_correlation import AutoCorrelationRequest, AutoCorrelationResponse
from app.models.correlation import CorrelationInput, CorrelationRequest, CorrelationResult
from app.repositories.correlation_repository import CorrelationRepository
from app.repositories.auto_correlation_repository import AutoCorrelationRepository
from app.services.correlation_service import CorrelationService

router = APIRouter(prefix="/correlations", tags=["correlations"])


def get_correlation_repository(connection=Depends(get_connection)):
    try:
        yield CorrelationRepository(connection)
    finally:
        connection.close()


import mysql.connector

@router.post("", response_model=CorrelationResult)
def correlate(
    request: CorrelationRequest,
    repository: CorrelationRepository = Depends(get_correlation_repository),
) -> CorrelationResult:
    result = CorrelationService().correlate(request.events)
    if not result.is_correlated:
        return result
    try:
        return repository.persist(result)
    except mysql.connector.Error as error:
        if getattr(error, "errno", None) == 1452:
            # Foreign key constraint failure (e.g. transaction_id or pid not in database tables)
            return result
        raise HTTPException(
            status_code=503,
            detail=f"Database error while persisting cross-layer trace: {error}",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to persist cross-layer trace: {error}",
        ) from error


@router.post("/auto", response_model=AutoCorrelationResponse)
def auto_correlate(
    request: AutoCorrelationRequest,
    connection=Depends(get_connection),
) -> AutoCorrelationResponse:
    try:
        candidates = AutoCorrelationRepository(connection)
        observation = candidates.observation(request.observation_id)
        if observation is None:
            raise HTTPException(status_code=404, detail="DBMS observation not found")

        # 1. Discover exact PID using the Live Identity Bridge
        from app.services.identity_bridge import IdentityBridgeService
        from app.config.settings import settings

        bridge = IdentityBridgeService(
            host=settings.mysql_host,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database="information_schema"
        )
        
        connection_id = observation.get("connection_id")
        discovered_pid = bridge.get_pid_for_connection(connection_id) if connection_id else None
        
        # 2. Find matching query executions (favoring the discovered PID if available)
        queries = candidates.matching_queries(observation, request.window_ms)
        if not queries:
            return AutoCorrelationResponse(
                observation_id=request.observation_id,
                reason="No matching query execution was found in the time window",
            )
        
        # If we discovered a PID, filter queries to that specific PID.
        if discovered_pid:
            exact_queries = [q for q in queries if q["pid"] == discovered_pid]
            if exact_queries:
                queries = exact_queries
                
        if len(queries) != 1:
            return AutoCorrelationResponse(
                observation_id=request.observation_id,
                reason=(
                    "Correlation is ambiguous: multiple query executions match "
                    "the DBMS observation and time window"
                ),
            )
        query = queries[0]

        # 3. Find matching OS events for the query's PID
        os_events = candidates.matching_os_events(query, request.window_ms)
        if not os_events:
            return AutoCorrelationResponse(
                observation_id=request.observation_id,
                matched_query_id=query["query_id"],
                reason="A query execution matched, but no nearby OS event was found",
            )

        from app.models.correlation_classification import CorrelationClassification

        # 4. Determine Classification and Evidence
        is_direct = (discovered_pid is not None and discovered_pid == query["pid"])
        classification_enum = CorrelationClassification.DIRECT if is_direct else CorrelationClassification.TEMPORAL
        evidence_reason = (
            f"DIRECT: PID {discovered_pid} verified via Identity Bridge (socket match to MySQL connection {connection_id})." 
            if is_direct else
            f"TEMPORAL: Matched via {request.window_ms}ms window (Identity Bridge PID: {discovered_pid}, Query PID: {query['pid']})."
        )

        inputs = [
            CorrelationInput(
                os_event_id=event["event_id"],
                pid=query["pid"],
                transaction_id=query["transaction_id"],
                query_id=query["query_id"],
                timestamp=event["timestamp"],
                event_type=event["event_type"],
                source="os_events",
                evidence_completeness=evidence_reason
            )
            for event in os_events
        ]
        result = CorrelationService().correlate(inputs)
        if result.is_correlated:
            result = result.model_copy(
                update={
                    "classification": classification_enum,
                    "evidence_summary": evidence_reason,
                    "correlations": [
                        item.model_copy(
                            update={
                                "db_event_id": request.observation_id,
                                "correlation_method": (
                                    "IDENTITY_BRIDGE_SOCKET_MATCH" if is_direct
                                    else "DBMS_OBSERVATION_QUERY_OS_TIMESTAMP"
                                ),
                            }
                        )
                        for item in result.correlations
                    ]
                }
            )
            if request.persist:
                result = CorrelationRepository(connection).persist(result)
        return AutoCorrelationResponse(
            observation_id=request.observation_id,
            matched_query_id=query["query_id"],
            matched_os_event_ids=[event["event_id"] for event in os_events],
            result=result,
            reason=result.reason,
        )
    except HTTPException:
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        connection.close()
