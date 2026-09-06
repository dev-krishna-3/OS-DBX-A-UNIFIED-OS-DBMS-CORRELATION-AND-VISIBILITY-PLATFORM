"""
Event service.

Temporary in-memory storage for OS events so the API contract and event
flow can be exercised before MySQL persistence is added in Milestone 2.

No database code belongs here yet - see repositories/event_repository.py
for where persistence will eventually live.
"""

import threading
from datetime import datetime, timezone

from app.models.events import OSEvent, StoredOSEvent

# Cap in-memory storage so a long-running dev server (or a collector
# hammering the endpoint) can't grow this unbounded. This is purely a
# safeguard for this temporary milestone - it goes away once MySQL
# persistence lands in Milestone 2.
MAX_STORED_EVENTS = 1000


class EventService:
    """Ingests and retrieves OS events using an in-memory store."""

    def __init__(self, max_events: int = MAX_STORED_EVENTS) -> None:
        self._events: list[StoredOSEvent] = []
        self._next_id: int = 1
        self._max_events = max_events
        self._lock = threading.Lock()

    def ingest_event(self, event: OSEvent) -> StoredOSEvent:
        """Store a validated event and return it with server-assigned metadata."""
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
        with self._lock:
            if limit <= 0:
                return []
            # Most recent last in storage order -> reverse for "most recent first".
            return list(reversed(self._events[-limit:]))


# Single shared instance for the app's lifetime (fine for an in-memory
# milestone; will be replaced by proper dependency injection once a real
# repository/database session is introduced).
event_service = EventService()
