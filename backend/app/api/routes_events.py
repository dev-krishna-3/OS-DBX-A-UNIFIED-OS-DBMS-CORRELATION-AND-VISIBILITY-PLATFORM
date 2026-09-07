"""
Event API routes.

    POST /api/events  - accept and validate one OS event, store it
    GET  /api/events   - return recently stored events

This is deliberately backed by the in-memory EventService for now.
MySQL persistence is Milestone 2.
"""

from fastapi import APIRouter, Query

from app.models.events import OSEvent, StoredOSEvent
from app.services.event_service import event_service

router = APIRouter(prefix="/events", tags=["events"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


@router.post("", response_model=StoredOSEvent, status_code=201)
def ingest_event(event: OSEvent) -> StoredOSEvent:
    """Validate an incoming OS event and store it. Returns the accepted event."""
    return event_service.ingest_event(event)


@router.get("", response_model=list[StoredOSEvent])
def list_events(
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Max number of recent events to return.",
    )
) -> list[StoredOSEvent]:
    """Return recently stored events, most recent first."""
    return event_service.get_events(limit=limit)
