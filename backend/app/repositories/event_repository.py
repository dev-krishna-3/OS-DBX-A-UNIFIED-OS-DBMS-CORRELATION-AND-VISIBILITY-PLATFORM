"""MySQL persistence for normalized OS events."""

import json
from datetime import datetime, timezone

from app.models.events import OSEvent, StoredOSEvent


def _mysql_datetime(value: datetime) -> datetime:
    """Convert an ISO timestamp into a timezone-naive UTC DATETIME value."""

    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class EventRepository:
    """Persist OS events in the ``os_events`` table using an injected connection."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def insert(self, event: OSEvent) -> StoredOSEvent:
        cursor = self.connection.cursor()
        try:
            timestamp = _mysql_datetime(event.timestamp)
            details = json.dumps({
                "ppid": event.ppid,
                "user": event.user,
                "process_name": event.process_name,
            })
            cursor.execute(
                """
                INSERT IGNORE INTO processes (pid, ppid, name, user, file_path, state)
                VALUES (%s, %s, %s, %s, %s, 'RUNNING')
                """,
                (
                    event.pid,
                    event.ppid,
                    event.process_name or "unknown",
                    event.user,
                    event.file_path,
                ),
            )
            cursor.execute(
                """
                INSERT INTO os_events (pid, event_type, file_path, details, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (event.pid, event.event_type.value, event.file_path, details, timestamp),
            )
            event_id = int(cursor.lastrowid)
            self.connection.commit()
            return StoredOSEvent(
                **event.model_dump(),
                id=event_id,
                received_at=datetime.now(timezone.utc),
            )
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def recent(self, limit: int) -> list[StoredOSEvent]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT event_id, pid, event_type, file_path, details, timestamp
                FROM os_events
                WHERE pid IS NOT NULL AND pid > 0
                ORDER BY event_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                details = row.get("details") or "{}"
                try:
                    metadata = json.loads(details) if isinstance(details, str) else (details or {})
                except (TypeError, json.JSONDecodeError):
                    metadata = {}
                ppid_val = metadata.get("ppid")
                try:
                    ppid_int = max(0, int(ppid_val)) if ppid_val is not None else 0
                except (ValueError, TypeError):
                    ppid_int = 0
                result.append(
                    StoredOSEvent(
                        timestamp=row["timestamp"],
                        pid=int(row["pid"]),
                        ppid=ppid_int,
                        process_name=metadata.get("process_name") or metadata.get("name"),
                        user=str(metadata.get("user") or "system"),
                        event_type=str(row["event_type"]),
                        file_path=row.get("file_path"),
                        id=int(row["event_id"]),
                        received_at=row["timestamp"],
                    )
                )
            return result
        finally:
            cursor.close()
