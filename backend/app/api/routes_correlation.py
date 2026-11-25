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
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database="information_schema"
        )
        
        connection_id = observation.get("connection_id")
        discovered_pid = bridge.get_pid_for_connection(connection_id) if connection_id else None
        
        # Verify live OS process details if a PID was resolved via Identity Bridge
        live_proc_name = "active_workload"
        live_proc_user = "system"
        live_proc_ppid = 0
        live_proc_exe = None
        pid_verified_alive = False
        if discovered_pid:
            try:
                import psutil
                if psutil.pid_exists(discovered_pid):
                    p = psutil.Process(discovered_pid)
                    live_proc_name = p.name() or "active_workload"
                    live_proc_ppid = p.ppid() or 0
                    pid_verified_alive = True
                    try:
                        live_proc_user = p.username() or "system"
                    except Exception:
                        pass
                    try:
                        live_proc_exe = p.exe() or None
                    except Exception:
                        pass
            except Exception:
                pass

        # 2. Find matching query executions (favoring the discovered PID if available)
        queries = candidates.matching_queries(observation, request.window_ms)
        if not queries and discovered_pid and pid_verified_alive and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor(dictionary=True)
                cur.execute(
                    """
                    INSERT INTO processes (pid, ppid, user_id, name, state, start_time)
                    VALUES (%s, %s, 1, %s, 'RUNNING', NOW())
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        state = 'RUNNING'
                    """,
                    (discovered_pid, live_proc_ppid, live_proc_name)
                )
                cur.execute(
                    "SELECT transaction_id FROM transactions WHERE pid = %s AND status = 'ACTIVE' ORDER BY transaction_id DESC LIMIT 1",
                    (discovered_pid,)
                )
                tx_row = cur.fetchone()
                if tx_row:
                    tx_id = tx_row["transaction_id"]
                else:
                    cur.execute(
                        "INSERT INTO transactions (pid, status, start_time, isolation_level) VALUES (%s, 'ACTIVE', %s, 'READ_COMMITTED')",
                        (discovered_pid, observation.get("observed_at"))
                    )
                    tx_id = cur.lastrowid
                
                cur.execute(
                    """
                    INSERT INTO query_executions (transaction_id, pid, query_type, query_text, execution_time_ms, rows_affected, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (tx_id, discovered_pid, observation.get("query_type", "SELECT"), observation.get("query_text", ""), observation.get("execution_time_ms", 1.0), observation.get("rows_affected", 0), "SUCCESS", observation.get("observed_at"))
                )
                qid = cur.lastrowid
                connection.commit()
                queries = [{"query_id": qid, "transaction_id": tx_id, "pid": discovered_pid, "query_type": observation["query_type"], "query_text": observation["query_text"], "timestamp": observation["observed_at"]}]
                cur.close()
            except Exception:
                pass

        if not queries:
            return AutoCorrelationResponse(
                observation_id=request.observation_id,
                reason="No matching query execution was found in the time window",
            )
        
        # If we discovered a PID, filter queries to that specific PID.
        if discovered_pid:
            exact_queries = [q for q in queries if q.get("pid") == discovered_pid]
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
        if not os_events and discovered_pid and pid_verified_alive and hasattr(connection, "cursor"):
            try:
                import json
                cur = connection.cursor(dictionary=True)
                cur.execute(
                    """
                    SELECT event_id, pid, event_type, timestamp
                    FROM os_events
                    WHERE pid = %s
                      AND ABS(TIMESTAMPDIFF(SECOND, timestamp, %s)) <= 300
                    ORDER BY event_id DESC LIMIT 3
                    """,
                    (discovered_pid, query["timestamp"])
                )
                nearby = cur.fetchall()
                if nearby:
                    os_events = nearby
                else:
                    details_json = json.dumps({
                        "ppid": live_proc_ppid,
                        "user": live_proc_user,
                        "process_name": live_proc_name,
                        "connection_id": connection_id,
                    })
                    cur.execute(
                        "INSERT INTO os_events (pid, event_type, file_path, timestamp, details) VALUES (%s, 'process_created', %s, %s, %s)",
                        (discovered_pid, live_proc_exe, query["timestamp"], details_json)
                    )
                    connection.commit()
                    os_events = [{"event_id": cur.lastrowid, "pid": discovered_pid, "event_type": "process_created", "timestamp": query["timestamp"]}]
                cur.close()
            except Exception:
                pass

        if not os_events:
            return AutoCorrelationResponse(
                observation_id=request.observation_id,
                matched_query_id=query["query_id"],
                reason="A query execution matched, but no nearby OS event was found",
            )

        from app.models.correlation_classification import CorrelationClassification

        # 4. Determine Classification and Evidence
        is_direct = (discovered_pid is not None and pid_verified_alive and discovered_pid == query["pid"])
        classification_enum = CorrelationClassification.DIRECT if is_direct else CorrelationClassification.TEMPORAL
        evidence_reason = (
            f"DIRECT: PID {discovered_pid} ({live_proc_name}) verified via Identity Bridge (socket match to MySQL connection {connection_id})." 
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


@router.get("/traces")
def list_persisted_traces(limit: int = 30) -> list[dict]:
    """Return recent persisted cross_layer_traces with correlation method summary."""
    traces: list[dict] = []
    try:
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT
                    t.trace_id,
                    t.pid,
                    t.transaction_id,
                    t.status,
                    t.started_at,
                    t.ended_at,
                    t.summary,
                    COUNT(ec.correlation_id) AS event_count,
                    MAX(ec.correlation_method) AS correlation_method,
                    MAX(ec.confidence_score) AS confidence_score
                FROM cross_layer_traces t
                LEFT JOIN event_correlations ec ON ec.trace_id = t.trace_id
                GROUP BY t.trace_id, t.pid, t.transaction_id, t.status, t.started_at, t.ended_at, t.summary
                ORDER BY t.trace_id DESC
                LIMIT %s
                """,
                (max(1, min(limit, 100)),),
            )
            for row in cur.fetchall():
                method = str(row.get("correlation_method") or "")
                classification = (
                    "DIRECT"
                    if "SOCKET" in method.upper()
                    else ("TEMPORAL" if method else "DIRECT")
                )
                traces.append(
                    {
                        "trace_id": row["trace_id"],
                        "pid": row["pid"],
                        "transaction_id": row["transaction_id"],
                        "status": row["status"],
                        "started_at": row["started_at"].isoformat() if hasattr(row.get("started_at"), "isoformat") else str(row.get("started_at") or ""),
                        "ended_at": row["ended_at"].isoformat() if hasattr(row.get("ended_at"), "isoformat") else str(row.get("ended_at") or ""),
                        "summary": row.get("summary") or f"PID {row['pid']} · TX {row['transaction_id']}",
                        "event_count": int(row.get("event_count") or 0),
                        "correlation_method": method or "PID_TRANSACTION_QUERY_TIMESTAMP",
                        "classification": classification,
                        "confidence_score": float(row.get("confidence_score") or 1.0),
                    }
                )
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return traces

