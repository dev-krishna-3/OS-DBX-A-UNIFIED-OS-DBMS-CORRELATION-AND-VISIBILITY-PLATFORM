"""
Event service.

OS event service supporting both local in-memory operation and an injected
durable repository.

No database code belongs here yet - see repositories/event_repository.py
for where persistence will eventually live.
"""

import threading
from datetime import datetime, timezone

from app.models.events import OSEvent, StoredOSEvent

# Cap in-memory storage so a long-running local dev server cannot grow it
# without bounds. MySQL-backed operation does not use this cap.
MAX_STORED_EVENTS = 1000


class EventService:
    """Ingests and retrieves OS events using memory or an injected repository."""

    def __init__(self, max_events: int = MAX_STORED_EVENTS, repository=None) -> None:
        self._events: list[StoredOSEvent] = []
        self._next_id: int = 1
        self._max_events = max_events
        self._lock = threading.Lock()
        self._repository = repository

    def ingest_event(self, event: OSEvent) -> StoredOSEvent:
        """Store a validated event and return it with server-assigned metadata."""
        if self._repository is not None:
            return self._repository.insert(event)
        with self._lock:
            stored = StoredOSEvent(
                **event.model_dump(),
                id=self._next_id,
                received_at=datetime.now(timezone.utc),
            )
            self._next_id += 1
            self._events.append(stored)
            if len(self._events) > self._max_events:
                # Drop the oldest events first.
                self._events = self._events[-self._max_events :]
            return stored

    def get_events(self, limit: int = 50) -> list[StoredOSEvent]:
        """Return the most recently ingested events, most recent first."""
        if self._repository is not None:
            return self._repository.recent(limit)
        with self._lock:
            if limit <= 0:
                return []
            # Most recent last in storage order -> reverse for "most recent first".
            return list(reversed(self._events[-limit:]))


# Single shared instance for local development and unit tests. The API creates
# a repository-backed service per request when EVENT_STORAGE=mysql is enabled.
event_service = EventService()
