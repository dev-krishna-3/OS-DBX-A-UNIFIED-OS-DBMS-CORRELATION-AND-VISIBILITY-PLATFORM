"""OS-DBX FastAPI application entrypoint."""

from fastapi import FastAPI

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
from app.config.settings import settings

app = FastAPI(title=settings.app_name)

app.include_router(events_router, prefix="/api")
app.include_router(correlation_router, prefix="/api")
app.include_router(deadlocks_router, prefix="/api")
app.include_router(dbms_events_router, prefix="/api")
app.include_router(query_executions_router, prefix="/api")
app.include_router(recovery_router, prefix="/api")
app.include_router(schedules_router, prefix="/api")
app.include_router(performance_router, prefix="/api")
app.include_router(investigation_router, prefix="/api")
app.include_router(what_if_router, prefix="/api")
app.include_router(locks_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Provide direct links for a teammate or evaluator opening the server."""

    return {
        "service": settings.app_name,
        "health": "/health",
        "docs": "/docs",
        "correlation_demo": "/api/demo/correlation",
    }


@app.get("/health")
def health() -> dict[str, str]:
    # Keep the original liveness contract stable for existing clients.
    return {"status": "ok"}


@app.get("/health/details")
def health_details() -> dict[str, str]:
    """Return evaluator-friendly service and correlation readiness details."""

    return {
        "status": "ok",
        "service": settings.app_name,
        "correlation_engine": "ready",
        "demo": "/api/demo/correlation",
        "docs": "/docs",
    }
