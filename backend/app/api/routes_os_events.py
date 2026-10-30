"""
OS event ingest routes — OS Live Reality Mode contract.

    POST /api/os-events            - ingest a process lifecycle event (pid required)
    POST /api/os-events/filesystem - ingest a filesystem event (pid intentionally null)
    GET  /api/os-events/metrics    - return stream metrics (dropped vs processed)

Filesystem events are accepted at a separate endpoint to make the null-PID
contract explicit and to avoid widening the existing ``OSEvent`` process model.

The ``WindowsAdapter`` is started in the FastAPI lifespan (see ``main.py``).
Events that arrive via the adapter are consumed from ``os_event_stream``
internally.  These POST endpoints are for direct injection (e.g. tests, other
team members, or the collector when the adapter is not running).
"""

from datetime import datetime, timezone

import threading

from fastapi import APIRouter, Request, Query, Depends
from app.api.routes_events import get_event_service
from app.services.event_service import EventService

from app.models.events import (
    OSEvent,
    OSFilesystemEvent,
    StoredOSEvent,
    StoredOSFilesystemEvent,
)
from app.config.settings import settings

router = APIRouter(prefix="/os-events", tags=["os-events"])

# ---------------------------------------------------------------------------
# In-memory stores for injected events (dev/test only).
# A durable repository would replace these when EVENT_STORAGE=mysql.
# ---------------------------------------------------------------------------

_process_events: list[StoredOSEvent] = []
_filesystem_events: list[StoredOSFilesystemEvent] = []
_next_process_id = 1
_next_filesystem_id = 1
_store_lock = threading.Lock()



@router.get("", response_model=list[StoredOSEvent])
def list_os_events(
    limit: int = Query(default=100, ge=1, le=500),
    service: EventService = Depends(get_event_service),
) -> list[StoredOSEvent]:
    """Return recently stored OS events (alias to /api/events for API consistency)."""
    return service.get_events(limit=limit)

@router.post("", response_model=StoredOSEvent, status_code=201)
def ingest_process_event(event: OSEvent) -> StoredOSEvent:
    """Accept and store one OS process lifecycle event (pid must be non-null).

    This endpoint is the ingest point for ``process_created`` and
    ``process_terminated`` events emitted by the OS collector.  When the
    ``WindowsAdapter`` is running, it feeds events into the in-process buffer
    (``os_event_stream``) instead.  Both paths honour the same event schema.
    """
    global _next_process_id

    with _store_lock:
        stored = StoredOSEvent(
            **event.model_dump(),
            id=_next_process_id,
            received_at=datetime.now(timezone.utc),
        )
        _next_process_id += 1
        _process_events.append(stored)
        # Bounded in-memory cap for development.
        if len(_process_events) > 1000:
            _process_events[:] = _process_events[-1000:]

    try:
        import json
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            ts = event.timestamp
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
            cur.execute(
                """
                INSERT INTO processes (pid, ppid, name, user, file_path, state)
                VALUES (%s, %s, %s, %s, %s, 'RUNNING')
                ON DUPLICATE KEY UPDATE
                    ppid = VALUES(ppid),
                    name = VALUES(name),
                    user = VALUES(user),
                    file_path = COALESCE(VALUES(file_path), file_path)
                """,
                (
                    event.pid,
                    event.ppid,
                    event.process_name or "unknown",
                    event.user,
                    event.file_path,
                ),
            )
            details = json.dumps({
                "event_id": event.event_id,
                "ppid": event.ppid,
                "user": event.user,
                "process_name": event.process_name,
                "host_id": event.host_id,
                "metadata": event.metadata or {},
            })
            cur.execute(
                """
                INSERT INTO os_events (pid, event_type, file_path, details, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event.pid,
                    event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                    event.file_path,
                    details,
                    ts,
                ),
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass

    return stored


@router.post("/filesystem", response_model=StoredOSFilesystemEvent, status_code=201)
def ingest_filesystem_event(event: OSFilesystemEvent) -> StoredOSFilesystemEvent:
    """Accept and store one OS filesystem event.

    Filesystem events intentionally carry ``pid=null``.  The OS contract
    does not substitute a fake PID; callers must never supply one here.
    The correlation engine uses time-window and ``file_path`` context for
    these events.
    """
    global _next_filesystem_id

    with _store_lock:
        stored = StoredOSFilesystemEvent(
            **event.model_dump(),
            id=_next_filesystem_id,
            received_at=datetime.now(timezone.utc),
        )
        _next_filesystem_id += 1
        _filesystem_events.append(stored)
        if len(_filesystem_events) > 1000:
            _filesystem_events[:] = _filesystem_events[-1000:]

    try:
        import json
        import os as _os
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            ts = event.timestamp
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
            ev_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            details = json.dumps({
                "event_id": event.event_id,
                "host_id": event.host_id,
                "operation": event.operation,
                "metadata": event.metadata or {},
            })
            cur.execute(
                """
                INSERT INTO os_events (pid, event_type, file_path, details, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (None, ev_type, event.file_path, details, ts),
            )
            if event.file_path:
                f_path = str(event.file_path)
                if ev_type in ("dir_created", "dir_deleted"):
                    cur.execute(
                        "INSERT IGNORE INTO directories (path) VALUES (%s)",
                        (f_path[:1024],),
                    )
                else:
                    dir_path = _os.path.dirname(f_path)
                    if dir_path:
                        cur.execute(
                            "INSERT IGNORE INTO directories (path) VALUES (%s)",
                            (dir_path[:1024],),
                        )
                    cur.execute(
                        """
                        INSERT INTO files (file_path, file_type, size_bytes, modified_at)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE modified_at = VALUES(modified_at)
                        """,
                        (
                            f_path[:1024],
                            (_os.path.splitext(f_path)[1].lstrip(".") or "file")[:50],
                            0,
                            ts,
                        ),
                    )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass

    return stored


@router.get("/metrics")
def get_stream_metrics(request: Request) -> dict:
    """Return observability metrics for the OS event stream.

    When the ``WindowsAdapter`` is initialised (via the FastAPI lifespan),
    live metrics from the burst-safe buffer are included under
    ``stream_metrics`` and ``adapter_health``.  If the adapter is not running
    (e.g. in unit tests), those keys will be absent.
    """
    metrics: dict = {
        "process_events_ingested": len(_process_events),
        "filesystem_events_ingested": len(_filesystem_events),
    }

    # Attempt to read live metrics from the adapter / event stream if available.
    app_state = getattr(request.app.state, "__dict__", {})

    os_stream = getattr(request.app.state, "os_event_stream", None)
    if os_stream is not None and hasattr(os_stream, "get_metrics"):
        metrics["stream_metrics"] = os_stream.get_metrics()

    adapter = getattr(request.app.state, "os_adapter", None)
    if adapter is not None and hasattr(adapter, "get_health"):
        metrics["adapter_health"] = adapter.get_health()

    return metrics


def is_adapter_running(adapter) -> bool:
    if adapter is None:
        return False
    return bool(getattr(adapter, "is_running", False) or getattr(adapter, "_running", False))


def ensure_adapter_started(app) -> tuple[bool, str]:
    adapter = getattr(app.state, "os_adapter", None)
    if is_adapter_running(adapter):
        return True, "OS watchdog filesystem collector is already running."

    try:
        try:
            from osdbx.adapters import WindowsAdapter  # type: ignore[import]
            from osdbx.stream import EventStream  # type: ignore[import]
        except ImportError:
            from os_monitor.adapters.windows_adapter import WindowsAdapter
            from os_monitor.core.stream import LiveEventStream as EventStream

        stream = getattr(app.state, "os_event_stream", None)
        if stream is None:
            stream = EventStream()
            app.state.os_event_stream = stream

        adapter = WindowsAdapter(
            stream=stream,
            watch_paths=getattr(settings, "os_watch_paths", ["."]),
        )
        adapter.start()
        app.state.os_adapter = adapter
        return True, "OS watchdog filesystem collector started successfully."
    except Exception as exc:
        return False, f"Could not start OS watchdog adapter: {exc}"


@router.post("/start")
def start_os_collector(request: Request) -> dict:
    """Manually or dynamically start the OS watchdog filesystem collector."""
    success, message = ensure_adapter_started(request.app)
    adapter = getattr(request.app.state, "os_adapter", None)
    is_running = is_adapter_running(adapter)
    return {
        "status": "RUNNING" if is_running else "STOPPED",
        "label": "[LIVE]" if is_running else "[OS MONITORING: STOPPED]",
        "is_active": is_running,
        "message": message,
        "watch_paths": getattr(settings, "os_watch_paths", []),
        "adapter_health": adapter.get_health() if adapter and hasattr(adapter, "get_health") else None,
    }


@router.get("/status")
def get_os_collector_status(request: Request) -> dict:
    """Return current operational status of the WindowsAdapter and Watchdog filesystem monitor."""
    adapter = getattr(request.app.state, "os_adapter", None)
    is_running = is_adapter_running(adapter)

    # Self-healing: if adapter is not running, attempt automatic start
    if not is_running:
        success, _ = ensure_adapter_started(request.app)
        if success:
            adapter = getattr(request.app.state, "os_adapter", None)
            is_running = is_adapter_running(adapter)

    return {
        "status": "RUNNING" if is_running else "STOPPED",
        "label": "[LIVE]" if is_running else "[OS MONITORING: STOPPED]",
        "is_active": is_running,
        "watch_paths": getattr(settings, "os_watch_paths", []),
        "adapter_health": adapter.get_health() if adapter and hasattr(adapter, "get_health") else None,
    }


@router.get("/filesystem")
def list_filesystem_events(limit: int = 50) -> list[dict]:
    """Return recent filesystem events from in-memory stream and database."""
    events = []
    with _store_lock:
        for e in _filesystem_events:
            d = e.model_dump()
            if hasattr(d.get("timestamp"), "isoformat"):
                d["timestamp"] = d["timestamp"].isoformat()
            if hasattr(d.get("received_at"), "isoformat"):
                d["received_at"] = d["received_at"].isoformat()
            events.append(d)

    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT event_id AS id, event_type, file_path, timestamp, details
                FROM os_events
                WHERE file_path IS NOT NULL OR event_type LIKE 'file_%' OR event_type LIKE 'dir_%'
                ORDER BY event_id DESC LIMIT %s
                """,
                (limit,)
            )
            for row in cur.fetchall():
                ts = row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"])
                events.append({
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "file_path": row.get("file_path"),
                    "timestamp": ts,
                    "received_at": ts,
                    "pid": None,
                    "source": "OS"
                })
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass

    # Deduplicate and sort newest first
    seen = set()
    unique_events = []
    for ev in events:
        key = (ev.get("event_type"), ev.get("file_path"), str(ev.get("timestamp") or ""))
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)
    unique_events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return unique_events[:limit]


_snapshot_cache: dict[str, tuple[float, list[dict]]] = {}
_snapshot_refreshing: set[str] = set()
_snapshot_lock = threading.Lock()
_SNAPSHOT_TTL_SECONDS = 10.0


def _cached_snapshot(key: str, builder) -> list[dict]:
    """Return a cached snapshot; refresh stale entries in the background.

    Process enumeration on Windows can take several seconds, so callers get the
    last snapshot immediately while a background thread rebuilds it.
    """
    import time as _time

    now = _time.monotonic()
    with _snapshot_lock:
        cached = _snapshot_cache.get(key)
        fresh = cached is not None and (now - cached[0]) < _SNAPSHOT_TTL_SECONDS
        should_refresh = not fresh and key not in _snapshot_refreshing
        if should_refresh and cached is not None:
            _snapshot_refreshing.add(key)

    def _rebuild() -> list[dict]:
        try:
            data = builder()
            with _snapshot_lock:
                _snapshot_cache[key] = (_time.monotonic(), data)
            return data
        finally:
            with _snapshot_lock:
                _snapshot_refreshing.discard(key)

    if cached is None:
        return _rebuild()
    if should_refresh:
        threading.Thread(target=_rebuild, daemon=True).start()
    return cached[1]


def _build_process_snapshot() -> list[dict]:
    try:
        from os_monitor.collector import snapshot_processes
        snapshot = snapshot_processes()
    except Exception:
        return []
    result = []
    for pid, info in snapshot.items():
        result.append({
            "pid": pid,
            "ppid": info.get("ppid"),
            "name": info.get("name"),
            "user": info.get("user"),
            "file_path": info.get("file_path"),
            "state": info.get("state")
        })
    sorted_res = sorted(result, key=lambda x: x["pid"])
    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            for proc in sorted_res[:200]:
                cur.execute(
                    """
                    INSERT INTO processes (pid, ppid, name, user, file_path, state)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        ppid = VALUES(ppid),
                        name = VALUES(name),
                        user = VALUES(user),
                        file_path = COALESCE(VALUES(file_path), file_path),
                        state = VALUES(state)
                    """,
                    (
                        proc["pid"],
                        proc.get("ppid"),
                        proc.get("name") or "unknown",
                        proc.get("user") or "system",
                        proc.get("file_path"),
                        str(proc.get("state") or "RUNNING")[:50],
                    ),
                )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return sorted_res


def _build_resource_snapshot() -> list[dict]:
    try:
        from os_monitor.resource_monitor import collect_metrics
        metrics = collect_metrics()
    except Exception:
        return []
    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            for m in metrics[:100]:
                pid = m.get("pid")
                if pid and int(pid) > 0:
                    cur.execute(
                        """
                        INSERT IGNORE INTO processes (pid, ppid, name, user, state)
                        VALUES (%s, 0, %s, %s, 'RUNNING')
                        """,
                        (int(pid), m.get("name") or "unknown", m.get("user") or "system"),
                    )
                    cur.execute(
                        """
                        INSERT INTO resource_metrics (pid, cpu_percent, memory_mb, io_read_bytes, io_write_bytes, timestamp)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            int(pid),
                            float(m.get("cpu_percent") or 0.0),
                            float(m.get("memory_rss_mb") or 0.0),
                            int(m.get("io_read_bytes") or 0),
                            int(m.get("io_write_bytes") or 0),
                        ),
                    )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return metrics


@router.get("/processes")
def list_processes(limit: int = 50) -> list[dict]:
    """Return real-time running process snapshot using Person 1's collector."""
    try:
        return _cached_snapshot("processes", _build_process_snapshot)[:limit]
    except Exception:
        return []


@router.get("/resources")
def list_resource_metrics(limit: int = 50) -> list[dict]:
    """Return real-time per-process resource metrics using Person 1's collector."""
    try:
        return _cached_snapshot("resources", _build_resource_snapshot)[:limit]
    except Exception:
        return []


