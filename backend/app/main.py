"""
OS-DBX backend - FastAPI application entrypoint.

Milestone 1 scope only: health check + event ingestion API backed by
in-memory storage. No MySQL, no correlation engine, no simulations yet.
"""

from fastapi import FastAPI

from app.api.routes_events import router as events_router
from app.api.routes_query_executions import router as query_executions_router
from app.api.routes_locks import router as locks_router
from app.api.routes_transactions import router as transactions_router
from app.config.settings import settings

app = FastAPI(title=settings.app_name)

app.include_router(events_router, prefix="/api")
app.include_router(query_executions_router, prefix="/api")
app.include_router(locks_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
