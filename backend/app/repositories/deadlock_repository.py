"""Database access for live lock snapshots and detected deadlock incidents."""

from datetime import datetime, timezone

from app.models.deadlocks import IncidentRecord, LockSnapshot


class DeadlockRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def active_locks(self) -> list[LockSnapshot]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT transaction_id, data_item, lock_type, status
                FROM locks
                WHERE status IN (%s, %s)
                ORDER BY transaction_id, lock_id
                """,
                ("HELD", "WAITING"),
            )
            return [LockSnapshot(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def record_deadlock(self, cycles: list[list[int]], graph: dict[str, list[int]]) -> int:
        cursor = self.connection.cursor()
        try:
            description = f"Wait-for cycle(s): {cycles}; graph: {graph}"
            # Repeated polling should reuse the open incident for the same
            # current wait-for graph instead of recording duplicates.
            cursor.execute(
                """
                SELECT incident_id
                FROM incidents
                WHERE incident_type = %s AND resolved = %s AND description = %s
                ORDER BY incident_id DESC
                LIMIT 1
                """,
                ("DEADLOCK", False, description),
            )
            existing = cursor.fetchone()
            if existing:
                self.connection.rollback()
                incident_id = (
                    existing["incident_id"]
                    if isinstance(existing, dict)
                    else existing[0]
                )
                return int(incident_id)

            cursor.execute(
                """
                INSERT INTO incidents
                    (trace_id, incident_type, description, detected_at, resolved)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    None,
                    "DEADLOCK",
                    description,
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    False,
                ),
            )
            incident_id = int(cursor.lastrowid)
            self.connection.commit()
            return incident_id
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def recent_incidents(self, limit: int = 50) -> list[IncidentRecord]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT incident_id, trace_id, incident_type, description,
                       detected_at, resolved
                FROM incidents
                ORDER BY detected_at DESC, incident_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [IncidentRecord(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()
