"""
Event API routes.

    POST /api/events  - accept and validate one OS event, store it
    GET  /api/events   - return recently stored events

Storage is selected by ``EVENT_STORAGE``. Local development defaults to the
in-memory service; production/integration environments can select MySQL.
"""

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.database import get_connection
from app.config.settings import settings
from app.core.tenancy import WorkspaceAccess, get_current_workspace
from app.models.events import OSEvent, StoredOSEvent
from app.repositories.event_repository import EventRepository
from app.services.event_service import event_service
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def get_event_service() -> Iterator[EventService]:
    """Use the configured event store; never silently downgrade durable storage."""
    storage = settings.event_storage.strip().lower()
    if storage == "memory":
        yield event_service
        return
    if storage != "mysql":
        raise HTTPException(status_code=500, detail="EVENT_STORAGE must be 'memory' or 'mysql'.")

    try:
        connection = get_connection()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Configured MySQL event storage is unavailable.") from error

    try:
        yield EventService(repository=EventRepository(connection))
    finally:
        connection.close()


@router.post("", response_model=StoredOSEvent, status_code=201)
def ingest_event(
    event: OSEvent,
    workspace: WorkspaceAccess = Depends(get_current_workspace),
    service: EventService = Depends(get_event_service),
) -> StoredOSEvent:
    """Validate an incoming OS event and store it. Returns the accepted event."""
    return service.ingest_event(event, workspace_id=workspace.workspace_id)


@router.get("", response_model=list[StoredOSEvent])
def list_events(
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Max number of recent events to return.",
    ),
    workspace: WorkspaceAccess = Depends(get_current_workspace),
    service: EventService = Depends(get_event_service),
) -> list[StoredOSEvent]:
    """Return recently stored events, most recent first."""
    return service.get_events(limit=limit, workspace_id=workspace.workspace_id)
