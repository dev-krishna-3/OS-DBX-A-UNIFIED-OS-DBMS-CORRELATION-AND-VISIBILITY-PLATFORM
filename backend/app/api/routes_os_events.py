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
