"""Persistence for trace and system performance measurements."""

from datetime import datetime, timezone

from app.models.performance import PerformanceRecord, PerformanceRecordCreate


class PerformanceRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def create(self, request: PerformanceRecordCreate) -> PerformanceRecord:
        recorded_at = request.recorded_at or datetime.now(timezone.utc).replace(tzinfo=None)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO performance_records
                    (trace_id, metric_name, metric_value, data_source, recorded_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (request.trace_id, request.metric_name, request.metric_value, request.data_source, recorded_at),
            )
            record_id = int(cursor.lastrowid)
            self.connection.commit()
            return PerformanceRecord(
                record_id=record_id,
                trace_id=request.trace_id,
                metric_name=request.metric_name,
                metric_value=request.metric_value,
                data_source=request.data_source,
                recorded_at=recorded_at,
            )
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def recent(self, limit: int = 50, trace_id: int | None = None) -> list[PerformanceRecord]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            query = """
                SELECT record_id, trace_id, metric_name, metric_value, data_source, recorded_at
                FROM performance_records
            """
            params: tuple = ()
            if trace_id is not None:
                query += " WHERE trace_id = %s"
                params = (trace_id,)
            query += " ORDER BY recorded_at DESC, record_id DESC LIMIT %s"
            cursor.execute(query, params + (limit,))
            return [PerformanceRecord(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()
