"""
Event API routes.

    POST /api/events  - accept and validate one OS event, store it
    GET  /api/events   - return recently stored events

Storage is selected by ``EVENT_STORAGE``. Local development defaults to the
in-memory service; production/integration environments can select MySQL.
"""

from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query

from app.config.database import get_connection
from app.config.settings import settings
from app.models.events import OSEvent, StoredOSEvent
from app.repositories.event_repository import EventRepository
from app.services.event_service import event_service
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def get_event_service() -> Iterator[EventService]:
    """Use durable storage only when explicitly enabled in configuration."""

    if settings.event_storage.lower() != "mysql":
        yield event_service
        return

    connection = get_connection()
    try:
        yield EventService(repository=EventRepository(connection))
    finally:
        connection.close()


@router.post("", response_model=StoredOSEvent, status_code=201)
def ingest_event(
    event: OSEvent,
    service: EventService = Depends(get_event_service),
) -> StoredOSEvent:
    """Validate an incoming OS event and store it. Returns the accepted event."""
    return service.ingest_event(event)


@router.get("", response_model=list[StoredOSEvent])
def list_events(
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Max number of recent events to return.",
    ),
    service: EventService = Depends(get_event_service),
) -> list[StoredOSEvent]:
    """Return recently stored events, most recent first."""
    return service.get_events(limit=limit)
