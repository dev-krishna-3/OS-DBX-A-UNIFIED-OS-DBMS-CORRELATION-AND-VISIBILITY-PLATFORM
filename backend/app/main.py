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
from app.config.settings import settings
from app.core.auth import get_current_user


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Start the OS adapter on startup and stop it on shutdown.

    The adapter feeds OS events into a burst-safe in-process buffer
    (``os_event_stream``).  Consumers pull from the buffer with
    ``os_event_stream.consume(block=False)``.

    If the ``osdbx-os-collector`` package is not installed, the adapter is
    skipped and both ``application.state.os_adapter`` and
    ``application.state.os_event_stream`` are set to ``None``.
    """
    try:
        from osdbx.adapters import WindowsAdapter  # type: ignore[import]
        from osdbx.stream import EventStream  # type: ignore[import]

        os_event_stream = EventStream()
        # watch_paths should be configured via settings or environment variable.
        # An empty list means the adapter monitors process events only.
        adapter = WindowsAdapter(
            stream=os_event_stream,
            watch_paths=getattr(settings, "os_watch_paths", []),
        )
        adapter.start()
        application.state.os_event_stream = os_event_stream
        application.state.os_adapter = adapter
    except ImportError:
        # Package not installed — adapter functionality unavailable.
        # The /health endpoint will reflect this; ingest routes still work.
        application.state.os_event_stream = None
        application.state.os_adapter = None

    yield  # Application runs here.

    # Shutdown: stop the adapter if it was started.
    adapter = getattr(application.state, "os_adapter", None)
    if adapter is not None and hasattr(adapter, "stop"):
        adapter.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
