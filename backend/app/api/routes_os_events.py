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

from fastapi import APIRouter, Request

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
        from osdbx.adapters import WindowsAdapter  # type: ignore[import]
        from osdbx.stream import EventStream  # type: ignore[import]

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
                WHERE file_path IS NOT NULL OR event_type LIKE 'file_%'
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


@router.get("/processes")
def list_processes(limit: int = 50) -> list[dict]:
    """Return real-time running process snapshot using Person 1's collector."""
    try:
        from os_monitor.collector import snapshot_processes
        snapshot = snapshot_processes()
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
        return sorted(result, key=lambda x: x["pid"])[:limit]
    except Exception as e:
        return []


@router.get("/resources")
def list_resource_metrics(limit: int = 50) -> list[dict]:
    """Return real-time per-process resource metrics using Person 1's collector."""
    try:
        from os_monitor.resource_monitor import collect_metrics
        metrics = collect_metrics()
        return metrics[:limit]
    except Exception as e:
        return []

