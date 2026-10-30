"""Interactive console endpoints mirroring the CLI unified console.

These endpoints give the web workspace the same capabilities the CLI exposes
through direct machine access:

    POST /api/console/sql              - run a read-only SQL statement and trace its causality
    GET  /api/console/real-world       - evaluate browser activity vs. DBMS workload causality
    POST /api/console/filesystem-test  - create/remove a real file and verify watcher detection
"""

from __future__ import annotations

import datetime
import os
import re
import time
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/console", tags=["console"])

_READ_ONLY = re.compile(r"^\s*(select|show|describe|desc|explain)\b", re.IGNORECASE)
_BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "chrome", "firefox", "msedge", "brave"}


class SqlConsoleRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    max_rows: int = Field(default=25, ge=1, le=200)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _process_snapshot(pid: int) -> dict:
    info: dict[str, Any] = {"pid": pid, "name": "osdbx-service", "user": "system", "cpu_percent": 0.0, "memory_percent": 0.0}
    try:
        import psutil

        proc = psutil.Process(pid)
        info["name"] = proc.name()
        try:
            info["user"] = proc.username()
        except Exception:
            pass
        info["cpu_percent"] = round(proc.cpu_percent(interval=None), 2)
        info["memory_percent"] = round(proc.memory_percent(), 2)
    except Exception:
        pass
    return info


def _local_port_for(pid: int, mysql_port: int) -> int | None:
    try:
        import psutil

        proc = psutil.Process(pid)
        getter = getattr(proc, "net_connections", None) or getattr(proc, "connections")
        for conn in getter(kind="tcp"):
            if conn.raddr and conn.raddr.port == mysql_port:
                return conn.laddr.port
    except Exception:
        return None
    return None


@router.post("/sql")
def run_sql_causality(request: SqlConsoleRequest) -> dict:
    """Execute one read-only statement, then trace it across the OS and DBMS layers."""
    query = request.query.strip().rstrip(";").strip()
    if ";" in query:
        raise HTTPException(status_code=400, detail="Run one statement at a time.")
    if not _READ_ONLY.match(query):
        raise HTTPException(
            status_code=400,
            detail="Only read-only statements are allowed here (SELECT, SHOW, DESCRIBE, EXPLAIN).",
        )

    import mysql.connector

    from app.config.database import get_connection
    from app.config.settings import settings

    pid = os.getpid()
    process = _process_snapshot(pid)
    columns: list[str] = []
    rows: list[list[Any]] = []
    total_rows = 0
    observation: dict | None = None
    correlation: dict | None = None
    local_port: int | None = None
    conn_id: int | None = None

    try:
        conn = mysql.connector.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
        )
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=f"Database is unavailable: {error.msg}") from error

    try:
        conn_id = conn.connection_id
        local_port = _local_port_for(pid, settings.mysql_port)
        started = time.perf_counter()
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            if cursor.description:
                columns = [d[0] for d in cursor.description]
                fetched = cursor.fetchall()
                total_rows = len(fetched)
                rows = [[_jsonable(v) for v in row] for row in fetched[: request.max_rows]]
            cursor.close()
        except mysql.connector.Error as error:
            raise HTTPException(status_code=400, detail=f"Query failed: {error.msg}") from error
        duration_ms = round((time.perf_counter() - started) * 1000, 3)

        # Harvest the statement from Performance Schema while the session is still open.
        try:
            from app.api.routes_dbms_events import _shared_seen_event_ids, _shared_seen_processlist
            from app.collectors.mysql_query_collector import MySQLQueryCollector
            from app.repositories.dbms_observation_repository import DBMSObservationRepository

            collect_conn = get_connection()
            try:
                collector = MySQLQueryCollector(
                    collect_conn,
                    seen_event_ids=_shared_seen_event_ids,
                    seen_processlist_queries=_shared_seen_processlist,
                )
                persisted = DBMSObservationRepository(collect_conn).insert_many(collector.poll(25))
                candidates = [o.model_dump(mode="json") for o in persisted]
                if not candidates:
                    candidates = [o.model_dump(mode="json") for o in DBMSObservationRepository(collect_conn).recent(10)]
            finally:
                collect_conn.close()
            normalized = query.lower()
            observation = next(
                (o for o in candidates if o.get("connection_id") == conn_id),
                None,
            ) or next(
                (o for o in candidates if normalized[:60] in str(o.get("query_text", "")).lower()),
                None,
            )
        except Exception:
            observation = None

        if observation and observation.get("observation_id"):
            try:
                from app.api.routes_correlation import auto_correlate
                from app.models.auto_correlation import AutoCorrelationRequest

                auto_res = auto_correlate(
                    AutoCorrelationRequest(observation_id=int(observation["observation_id"]), window_ms=10000, persist=True),
                    connection=get_connection(),
                )
                correlation = auto_res.model_dump(mode="json")
            except Exception as error:  # correlation is best-effort evidence
                correlation = {"reason": str(getattr(error, "detail", error))}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    result = (correlation or {}).get("result") or {}
    classification = result.get("classification") or ("TEMPORAL" if observation else "NOT_CORRELATED")
    return {
        "query": query,
        "columns": columns,
        "rows": rows,
        "row_count": total_rows,
        "duration_ms": duration_ms,
        "connection_id": conn_id,
        "process": process,
        "socket": {"local_port": local_port, "remote_port": settings.mysql_port},
        "observation": observation,
        "correlation": correlation,
        "classification": classification,
        "trace_id": (result.get("trace") or {}).get("trace_id"),
    }


@router.get("/real-world")
def evaluate_real_world_activity() -> dict:
    """Prove whether a browser workload is causally linked to the DBMS (it usually is not)."""
    from app.config.database import get_connection
    from app.config.settings import settings

    browser_pids: list[int] = []
    browser_name: str | None = None
    try:
        import psutil

        for proc in psutil.process_iter(["pid", "name"]):
            name = (proc.info.get("name") or "").lower()
            if name in _BROWSERS:
                browser_pids.append(proc.info["pid"])
                browser_name = browser_name or proc.info.get("name")
    except Exception:
        pass

    mapping: dict[int, int] = {}
    try:
        from app.services.identity_bridge import IdentityBridgeService

        bridge = IdentityBridgeService(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database="information_schema",
        )
        mapping = bridge.build_pid_to_connection_map()
    except Exception:
        mapping = {}

    observation: dict | None = None
    try:
        from app.repositories.dbms_observation_repository import DBMSObservationRepository

        conn = get_connection()
        try:
            recent = DBMSObservationRepository(conn).recent(1)
            observation = recent[0].model_dump(mode="json") if recent else None
        finally:
            conn.close()
    except Exception:
        observation = None

    owning = [pid for pid in browser_pids if pid in mapping]
    linked = bool(owning)
    return {
        "browser": {"name": browser_name, "pids": browser_pids[:6], "running": bool(browser_pids)},
        "bridged_processes": [{"os_pid": pid, "mysql_connection_id": cid} for pid, cid in mapping.items()],
        "observation": observation,
        "browser_owns_mysql_connection": linked,
        "classification": "DIRECT" if linked else "NOT_CORRELATED",
        "reason": (
            "The browser process owns a TCP connection to the database port, so its activity is directly linked."
            if linked
            else "The browser owns no connection to the database port. Even if both happened at the same second, "
            "timing alone never proves causality."
        ),
    }


@router.post("/filesystem-test")
def run_filesystem_detection_test() -> dict:
    """Create and remove a real file, then verify the filesystem watcher captured it."""
    from app.api import routes_os_events
    from app.models.events import OSFilesystemEvent

    file_name = f"os_dbx_live_watch_test_{int(time.time() * 1000)}.tmp"
    file_path = os.path.abspath(file_name)
    created_at = datetime.datetime.now(datetime.timezone.utc)
    try:
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(f"OS-DBX live detection test at {created_at.isoformat()}\n")
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Could not create test file: {error}") from error

    detected = None
    deadline = time.time() + 1.5
    while time.time() < deadline and detected is None:
        time.sleep(0.25)
        for event in reversed(routes_os_events._filesystem_events[-200:]):
            if file_name in str(event.file_path or ""):
                detected = event
                break

    watcher_detected = detected is not None
    if detected is None:
        detected = routes_os_events.ingest_filesystem_event(
            OSFilesystemEvent(timestamp=created_at, event_type="file_created", file_path=file_path)
        )

    cleaned = False
    try:
        os.remove(file_path)
        cleaned = True
        routes_os_events.ingest_filesystem_event(
            OSFilesystemEvent(
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                event_type="file_deleted",
                file_path=file_path,
            )
        )
    except Exception:
        pass

    return {
        "file_path": file_path,
        "watcher_detected": watcher_detected,
        "event": detected.model_dump(mode="json"),
        "cleaned_up": cleaned,
    }
