"""OS-DBX FastAPI application entrypoint.

OS Live Reality Mode — adapter lifecycle
-----------------------------------------
The ``WindowsAdapter`` (from the ``osdbx-os-collector`` package published by
Person 1) is started in a ``lifespan`` context manager so it runs in the
background for the duration of the server process and is cleanly stopped on
shutdown.  HTTP route handlers must never start or stop the adapter directly.

If the package is not installed (e.g. in CI or on non-Windows machines), the
adapter block degrades gracefully: the health endpoints still respond, and the
``/api/os-events`` ingest endpoints remain available for direct injection.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends

from app.api.routes_auth import router as auth_router
from app.api.routes_events import router as events_router
from app.api.routes_correlation import router as correlation_router
from app.api.routes_deadlocks import router as deadlocks_router
from app.api.routes_dbms_events import router as dbms_events_router
from app.api.routes_query_executions import router as query_executions_router
from app.api.routes_recovery import router as recovery_router
from app.api.routes_schedules import router as schedules_router
from app.api.routes_performance import router as performance_router
from app.api.routes_investigation import router as investigation_router
from app.api.routes_what_if import router as what_if_router
from app.api.routes_locks import router as locks_router
from app.api.routes_transactions import router as transactions_router
from app.api.routes_demo import router as demo_router
from app.api.routes_benchmark import router as benchmark_router
from app.api.routes_blast_radius import router as blast_radius_router
from app.api.routes_os_events import router as os_events_router
from app.api.routes_simulations import router as simulations_router
from app.api.routes_audit import router as audit_router
from app.api.routes_bridge import router as bridge_router
from app.api.routes_console import router as console_router
from app.config.settings import settings
from app.core.auth import get_current_user


def seed_admin_account() -> None:
    """Ensure a development/test admin account and email column exist safely."""
    import os
    from app.config.database import get_connection
    from app.core.auth import get_password_hash
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@OSDBX2026!")
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL UNIQUE")
            conn.commit()
        except Exception:
            pass
        cur.execute("SELECT user_id, is_admin FROM users WHERE username = 'admin'")
        row = cur.fetchone()
        if not row:
            hashed = get_password_hash(admin_password)
            cur.execute(
                "INSERT INTO users (username, uid_linux, password_hash, is_admin) VALUES ('admin', 0, %s, 1)",
                (hashed,)
            )
            conn.commit()
        elif not row.get("is_admin"):
            cur.execute("UPDATE users SET is_admin = 1, uid_linux = 0 WHERE username = 'admin'")
            conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Start the OS adapter and automatic DBMS observation on startup and stop on shutdown."""
    import asyncio
    from app.config.database import get_connection

    seed_admin_account()
    try:
        import threading as _threading
        from app.api import routes_os_events as _os_routes

        _threading.Thread(
            target=lambda: (_os_routes.list_processes(), _os_routes.list_resource_metrics()),
            daemon=True,
        ).start()
    except Exception:
        pass
    consumer_task = None
    dbms_task = None
    os_task = None

    # Continuous automatic OS process and resource monitor (Person 1 collector)
    async def _consume_os_poller():
        from app.api import routes_os_events as _os_routes
        while True:
            try:
                await asyncio.sleep(4.0)
                _os_routes.list_processes()
                _os_routes.list_resource_metrics()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5.0)
    
    # 1. Start continuous automatic DBMS observation poller
    async def _consume_dbms_poller():
        import psutil
        from app.collectors.mysql_query_collector import MySQLQueryCollector
        from app.repositories.dbms_observation_repository import DBMSObservationRepository
        from app.services.identity_bridge import IdentityBridgeService
        from app.api.routes_dbms_events import _shared_seen_event_ids, _shared_seen_processlist
        while True:
            try:
                await asyncio.sleep(1.5)
                conn = get_connection()
                try:
                    collector = MySQLQueryCollector(
                        conn,
                        seen_event_ids=_shared_seen_event_ids,
                        seen_processlist_queries=_shared_seen_processlist,
                    )
                    observations = collector.poll(limit=25)
                    if observations:
                        repo = DBMSObservationRepository(conn)
                        persisted = repo.insert_many(observations)
                        bridge = IdentityBridgeService(
                            host=settings.mysql_host,
                            port=settings.mysql_port,
                            user=settings.mysql_user,
                            password=settings.mysql_password,
                            database="information_schema"
                        )
                        pid_map = bridge.build_pid_to_connection_map()
                        cur = conn.cursor(dictionary=True)
                        for obs in persisted:
                            matched_pid = None
                            if obs.connection_id:
                                matched_pid = next((p for p, c in pid_map.items() if c == obs.connection_id), None)
                                if matched_pid is None:
                                    matched_pid = bridge.get_pid_for_connection(obs.connection_id)
                            if matched_pid:
                                pname = "active_workload"
                                try:
                                    pname = psutil.Process(matched_pid).name() or "active_workload"
                                except Exception:
                                    pass
                                cur.execute(
                                    """
                                    INSERT INTO processes (pid, name, state, start_time)
                                    VALUES (%s, %s, 'RUNNING', %s)
                                    ON DUPLICATE KEY UPDATE state = 'RUNNING', name = COALESCE(VALUES(name), name)
                                    """,
                                    (matched_pid, pname, obs.observed_at)
                                )
                                cur.execute(
                                    "SELECT transaction_id FROM transactions WHERE pid = %s AND status = 'ACTIVE' ORDER BY transaction_id DESC LIMIT 1",
                                    (matched_pid,)
                                )
                                tx_row = cur.fetchone()
                                if tx_row:
                                    tx_id = tx_row["transaction_id"]
                                else:
                                    cur.execute(
                                        "INSERT INTO transactions (pid, status, start_time, isolation_level) VALUES (%s, 'ACTIVE', %s, 'READ_COMMITTED')",
                                        (matched_pid, obs.observed_at)
                                    )
                                    tx_id = cur.lastrowid

                                cur.execute(
                                    """
                                    SELECT query_id FROM query_executions
                                    WHERE pid = %s AND query_text = %s
                                      AND ABS(TIMESTAMPDIFF(SECOND, timestamp, %s)) <= 5
                                    ORDER BY query_id DESC LIMIT 1
                                    """,
                                    (matched_pid, obs.query_text, obs.observed_at)
                                )
                                q_row = cur.fetchone()
                                if q_row:
                                    qid = q_row["query_id"]
                                else:
                                    cur.execute(
                                        """
                                        INSERT INTO query_executions (transaction_id, pid, query_type, query_text, execution_time_ms, rows_affected, status, timestamp)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        """,
                                        (tx_id, matched_pid, obs.query_type, obs.query_text, obs.execution_time_ms, obs.rows_affected, obs.status, obs.observed_at)
                                    )
                                    qid = cur.lastrowid

                                cur.execute(
                                    "SELECT event_id FROM os_events WHERE pid = %s ORDER BY event_id DESC LIMIT 1",
                                    (matched_pid,)
                                )
                                os_ev = cur.fetchone()
                                if not os_ev and psutil.pid_exists(matched_pid):
                                    cur.execute(
                                        "INSERT INTO os_events (pid, event_type, timestamp, details) VALUES (%s, 'process_created', %s, %s)",
                                        (matched_pid, obs.observed_at, f'{{"process_name": "{pname}", "connection_id": {obs.connection_id}}}')
                                    )
                                    os_ev = {"event_id": cur.lastrowid}

                                if os_ev:
                                    cur.execute(
                                        "SELECT correlation_id FROM event_correlations WHERE db_event_id = %s LIMIT 1",
                                        (obs.observation_id,)
                                    )
                                    if not cur.fetchone():
                                        cur.execute(
                                            """
                                            INSERT INTO cross_layer_traces (pid, transaction_id, started_at, ended_at, summary, status)
                                            VALUES (%s, %s, %s, %s, %s, 'COMPLETED')
                                            """,
                                            (
                                                matched_pid,
                                                tx_id,
                                                obs.observed_at,
                                                obs.observed_at,
                                                f"Auto-correlation (Obs #{obs.observation_id}): PID {matched_pid} <-> Conn {obs.connection_id} | {obs.query_text[:40]}"
                                            )
                                        )
                                        new_tid = cur.lastrowid
                                        cur.execute(
                                            """
                                            INSERT INTO event_correlations (trace_id, os_event_id, db_event_id, query_id, correlation_method, confidence_score, sequence_order)
                                            VALUES (%s, %s, %s, %s, 'IDENTITY_BRIDGE_SOCKET_MATCH', 1.0, 1)
                                            """,
                                            (new_tid, os_ev["event_id"], obs.observation_id, qid)
                                        )
                        conn.commit()
                        cur.close()
                except Exception:
                    conn.rollback()
                finally:
                    conn.close()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2.0)

    try:
        dbms_task = asyncio.create_task(_consume_dbms_poller())
        os_task = asyncio.create_task(_consume_os_poller())
    except Exception:
        pass

    try:
        import os as _os
        import sys as _sys
        from datetime import datetime, timezone
        import json as _json

        _proj_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
        if _proj_root not in _sys.path:
            _sys.path.insert(0, _proj_root)

        try:
            from osdbx.adapters import WindowsAdapter  # type: ignore[import]
            from osdbx.stream import EventStream  # type: ignore[import]
        except ImportError:
            from os_monitor.adapters.windows_adapter import WindowsAdapter
            from os_monitor.core.stream import LiveEventStream as EventStream

        os_event_stream = EventStream()
        adapter = WindowsAdapter(
            stream=os_event_stream,
            watch_paths=getattr(settings, "os_watch_paths", ["."]),
        )
        adapter.start()
        application.state.os_event_stream = os_event_stream
        application.state.os_adapter = adapter
        
        async def _consume_stream():
            while True:
                try:
                    first_ev = os_event_stream.consume(block=False)
                    if first_ev is not None:
                        batch = first_ev if isinstance(first_ev, list) else [first_ev]
                        while len(batch) < 25:
                            nxt = os_event_stream.consume(block=False)
                            if nxt is None:
                                break
                            if isinstance(nxt, list):
                                batch.extend(nxt)
                            else:
                                batch.append(nxt)

                        conn = get_connection()
                        try:
                            cursor = conn.cursor()
                            for item in batch:
                                ev = item.to_dict() if hasattr(item, "to_dict") else (item if isinstance(item, dict) else {})
                                if not ev:
                                    continue
                                pid = ev.get("pid")
                                ev_type = str(ev.get("event_type") or "")
                                raw_ts = ev.get("timestamp")
                                if isinstance(raw_ts, (int, float)):
                                    ts = datetime.fromtimestamp(float(raw_ts), tz=timezone.utc).replace(tzinfo=None)
                                elif isinstance(raw_ts, datetime):
                                    ts = raw_ts.astimezone(timezone.utc).replace(tzinfo=None) if raw_ts.tzinfo else raw_ts
                                else:
                                    ts = datetime.now(timezone.utc).replace(tzinfo=None)
                                fpath = ev.get("file_path")
                                meta = ev.get("metadata") or {}
                                details_str = _json.dumps({
                                    "process_name": ev.get("process_name"),
                                    "ppid": meta.get("ppid", 0),
                                    "user": meta.get("user", "system"),
                                    "host_id": ev.get("host_id"),
                                    "evidence_completeness": ev.get("evidence_completeness"),
                                })

                                cursor.execute(
                                    "INSERT INTO os_events (pid, event_type, timestamp, file_path, details) VALUES (%s, %s, %s, %s, %s)",
                                    (pid if (pid and pid > 0) else None, ev_type, ts, fpath, details_str)
                                )

                                # Populate processes table
                                if pid and pid > 0:
                                    pname = ev.get("process_name") or "os_process"
                                    ppid_val = meta.get("ppid")
                                    res_info = ev.get("resource_info") or {}
                                    cpu_val = res_info.get("cpu_usage")
                                    mem_val = res_info.get("memory_usage")
                                    cursor.execute(
                                        """
                                        INSERT INTO processes (pid, ppid, name, state, cpu_percent, memory_percent, start_time)
                                        VALUES (%s, %s, %s, 'RUNNING', %s, %s, %s)
                                        ON DUPLICATE KEY UPDATE
                                            state = 'RUNNING',
                                            name = COALESCE(VALUES(name), name),
                                            ppid = COALESCE(VALUES(ppid), ppid),
                                            cpu_percent = COALESCE(VALUES(cpu_percent), cpu_percent),
                                            memory_percent = COALESCE(VALUES(memory_percent), memory_percent)
                                        """,
                                        (pid, ppid_val, pname, cpu_val, mem_val, ts)
                                    )
                                    if ev_type == "process_terminated":
                                        cursor.execute(
                                            "UPDATE processes SET state = 'TERMINATED', end_time = %s WHERE pid = %s",
                                            (ts, pid)
                                        )

                                    # Populate resource_metrics & threads if telemetry is attached
                                    cursor.execute("SELECT process_id FROM processes WHERE pid = %s LIMIT 1", (pid,))
                                    p_row = cursor.fetchone()
                                    if p_row:
                                        proc_id = p_row[0]
                                        if res_info:
                                            cursor.execute(
                                                """
                                                INSERT INTO resource_metrics (process_id, cpu_usage, memory_usage, disk_io, network_io, recorded_at)
                                                VALUES (%s, %s, %s, %s, %s, %s)
                                                """,
                                                (proc_id, res_info.get("cpu_usage"), res_info.get("memory_usage"), res_info.get("disk_io"), res_info.get("network_io"), ts)
                                            )
                                        threads_list = meta.get("threads") or []
                                        for t in threads_list[:3]:
                                            tid = t.get("id")
                                            if tid:
                                                cursor.execute(
                                                    "INSERT IGNORE INTO threads (process_id, tid, state, created_at) VALUES (%s, %s, 'RUNNING', %s)",
                                                    (proc_id, tid, ts)
                                                )

                                # Populate files, directories, permissions for filesystem events
                                if fpath and ev_type.startswith("file_"):
                                    cursor.execute("INSERT IGNORE INTO files (file_path, size_bytes) VALUES (%s, %s)", (fpath, 0))
                                    dpath = _os.path.dirname(fpath) or fpath
                                    cursor.execute("INSERT IGNORE INTO directories (path) VALUES (%s)", (dpath,))
                                    cursor.execute("SELECT file_id FROM files WHERE file_path = %s LIMIT 1", (fpath,))
                                    f_row = cursor.fetchone()
                                    if f_row:
                                        cursor.execute(
                                            "INSERT IGNORE INTO permissions (file_id, user_id, access_type, granted_at) VALUES (%s, 1, 'READ_WRITE', %s)",
                                            (f_row[0], ts)
                                        )
                            conn.commit()
                            cursor.close()
                        except Exception:
                            conn.rollback()
                        finally:
                            conn.close()
                    await asyncio.sleep(0.05)
                except asyncio.CancelledError:
                    break
                except Exception:
                    await asyncio.sleep(0.1)

        consumer_task = asyncio.create_task(_consume_stream())

    except ImportError:
        application.state.os_event_stream = None
        application.state.os_adapter = None

    yield  # Application runs here.

    if consumer_task:
        consumer_task.cancel()
    if dbms_task:
        dbms_task.cancel()
    if os_task:
        os_task.cancel()

    # Shutdown: stop the adapter if it was started.
    adapter = getattr(application.state, "os_adapter", None)
    if adapter is not None and hasattr(adapter, "stop"):
        adapter.stop()


from fastapi.middleware.cors import CORSMiddleware

is_production = settings.environment.lower() in ("production", "prod")
app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")

# Protected Routes
secure = [Depends(get_current_user)]
app.include_router(events_router, prefix="/api", dependencies=secure)
app.include_router(correlation_router, prefix="/api", dependencies=secure)
app.include_router(deadlocks_router, prefix="/api", dependencies=secure)
app.include_router(dbms_events_router, prefix="/api", dependencies=secure)
app.include_router(query_executions_router, prefix="/api", dependencies=secure)
app.include_router(recovery_router, prefix="/api", dependencies=secure)
app.include_router(schedules_router, prefix="/api", dependencies=secure)
app.include_router(performance_router, prefix="/api", dependencies=secure)
app.include_router(investigation_router, prefix="/api", dependencies=secure)
app.include_router(what_if_router, prefix="/api", dependencies=secure)
app.include_router(locks_router, prefix="/api", dependencies=secure)
app.include_router(transactions_router, prefix="/api", dependencies=secure)
app.include_router(benchmark_router, dependencies=secure)
app.include_router(blast_radius_router, dependencies=secure)
app.include_router(os_events_router, prefix="/api", dependencies=secure)
app.include_router(simulations_router, prefix="/api", dependencies=secure)
app.include_router(audit_router, prefix="/api/audit", dependencies=secure)
app.include_router(bridge_router, prefix="/api", dependencies=secure)
app.include_router(console_router, prefix="/api", dependencies=secure)

# Demo routes remain open for evaluators
app.include_router(demo_router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Provide direct links for a teammate or evaluator opening the server."""

    return {
        "service": settings.app_name,
        "health": "/health",
        "docs": "/docs",
        "correlation_demo": "/api/demo/correlation",
        "os_events": "/api/os-events",
        "os_filesystem_events": "/api/os-events/filesystem",
        "os_stream_metrics": "/api/os-events/metrics",
    }


@app.get("/health")
def health() -> dict[str, str]:
    # Keep the original liveness contract stable for existing clients.
    return {"status": "ok"}


@app.get("/health/details")
def health_details() -> dict:
    """Return evaluator-friendly service, correlation, and OS stream details.

    ``os_stream_metrics`` shows the burst-safe buffer counters (received,
    processed, dropped).  ``os_adapter_health`` shows whether the Windows
    adapter is running.  Both keys are present only when the
    ``osdbx-os-collector`` package is installed and the adapter started
    successfully.
    """
    details: dict = {
        "status": "ok",
        "service": settings.app_name,
        "correlation_engine": "ready",
        "demo": "/api/demo/correlation",
        "docs": "/docs",
    }

    os_stream = getattr(app.state, "os_event_stream", None)
    if os_stream is not None and hasattr(os_stream, "get_metrics"):
        details["os_stream_metrics"] = os_stream.get_metrics()
    else:
        details["os_stream_metrics"] = None
        details["os_adapter_note"] = (
            "WindowsAdapter not running — osdbx-os-collector package may not be "
            "installed.  Ingest via POST /api/os-events is still available."
        )

    os_adapter = getattr(app.state, "os_adapter", None)
    if os_adapter is not None and hasattr(os_adapter, "get_health"):
        details["os_adapter_health"] = os_adapter.get_health()
    else:
        details["os_adapter_health"] = None

    return details
