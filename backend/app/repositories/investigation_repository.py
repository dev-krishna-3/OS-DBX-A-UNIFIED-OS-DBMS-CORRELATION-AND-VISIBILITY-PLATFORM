"""Read and replay persistence for incident investigations."""

import json
from datetime import datetime, timezone
from typing import Any

from app.models.deadlocks import IncidentRecord
from app.models.investigation import (
    IncidentInvestigation,
    IncidentReplay,
    InvestigationTimelineEntry,
)
from app.models.performance import PerformanceRecord


class IncidentNotFoundError(Exception):
    """Raised when an incident ID does not exist."""


class ReplayUnavailableError(Exception):
    """Raised when an incident has no linked, correlated trace to replay."""


class InvestigationRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def investigate(self, incident_id: int) -> IncidentInvestigation:
        incident = self._incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError(incident_id)

        trace = self._trace(incident.trace_id)
        transaction_id = trace.get("transaction_id") if trace else None
        timeline: list[InvestigationTimelineEntry] = []

        if trace:
            timeline.append(
                InvestigationTimelineEntry(
                    sequence=1,
                    source="trace",
                    source_id=trace["trace_id"],
                    timestamp=trace.get("started_at"),
                    event_type="TRACE_STARTED",
                    description=trace.get("summary") or "Cross-layer trace started",
                    payload=trace,
                )
            )

        timeline.extend(self._correlation_timeline(incident.trace_id, len(timeline)))
        if transaction_id is not None:
            timeline.extend(self._transaction_timeline(transaction_id, len(timeline)))

        timeline.sort(key=lambda item: (item.timestamp or datetime.min, item.sequence))
        timeline = [item.model_copy(update={"sequence": index}) for index, item in enumerate(timeline, 1)]
        performance = self._performance(incident.trace_id)
        return IncidentInvestigation(
            incident=incident,
            trace=trace,
            timeline=timeline,
            performance=performance,
        )

    def save_replay(self, investigation: IncidentInvestigation) -> IncidentReplay:
        if investigation.trace is None:
            raise ReplayUnavailableError("Incident has no linked cross-layer trace")
        if not any(step.source == "correlation" for step in investigation.timeline):
            raise ReplayUnavailableError(
                "Linked trace has no correlated events; replay requires at least one correlation"
            )

        replayed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        steps = investigation.timeline
        summary = (
            f"Replayed {len(steps)} recorded step(s) for incident "
            f"{investigation.incident.incident_id}; no live SQL was executed."
        )
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO incident_replays
                    (incident_id, replayed_at, outcome, steps_json, summary)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    investigation.incident.incident_id,
                    replayed_at,
                    "REPLAYED",
                    json.dumps([step.model_dump(mode="json") for step in steps]),
                    summary,
                ),
            )
            replay_id = int(cursor.lastrowid)
            self.connection.commit()
            return IncidentReplay(
                replay_id=replay_id,
                incident_id=investigation.incident.incident_id,
                replayed_at=replayed_at,
                outcome="REPLAYED",
                steps=steps,
                summary=summary,
            )
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _incident(self, incident_id: int) -> IncidentRecord | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT incident_id, trace_id, incident_type, description,
                       detected_at, resolved
                FROM incidents
                WHERE incident_id = %s
                """,
                (incident_id,),
            )
            row = cursor.fetchone()
            return IncidentRecord(**row) if row else None
        finally:
            cursor.close()

    def _trace(self, trace_id: int | None) -> dict[str, Any] | None:
        if trace_id is None:
            return None
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT trace_id, pid, transaction_id, status, started_at,
                       ended_at, summary
                FROM cross_layer_traces
                WHERE trace_id = %s
                """,
                (trace_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()

    def _correlation_timeline(self, trace_id: int | None, offset: int) -> list[InvestigationTimelineEntry]:
        if trace_id is None:
            return []
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT ec.correlation_id, ec.sequence_order, ec.correlation_method,
                       ec.confidence_score, oe.event_id, oe.event_type,
                       oe.timestamp AS os_timestamp, oe.pid, oe.file_path,
                       qe.query_id, qe.query_type, qe.query_text,
                       qe.execution_time_ms, qe.rows_affected, qe.status,
                       qe.timestamp AS query_timestamp
                FROM event_correlations AS ec
                LEFT JOIN os_events AS oe ON oe.event_id = ec.os_event_id
                LEFT JOIN query_executions AS qe ON qe.query_id = ec.query_id
                WHERE ec.trace_id = %s
                ORDER BY ec.sequence_order, ec.correlation_id
                """,
                (trace_id,),
            )
            result = []
            for row in cursor.fetchall():
                timestamp = row.get("query_timestamp") or row.get("os_timestamp")
                description = row.get("query_text") or row.get("event_type") or "Correlated event"
                result.append(
                    InvestigationTimelineEntry(
                        sequence=offset + len(result) + 1,
                        source="correlation",
                        source_id=row.get("correlation_id"),
                        timestamp=timestamp,
                        event_type=row.get("query_type") or row.get("event_type") or "CORRELATED",
                        description=description,
                        payload={
                            "os_event_id": row.get("event_id"),
                            "query_id": row.get("query_id"),
                            "pid": row.get("pid"),
                            "correlation_method": row.get("correlation_method"),
                            "confidence_score": row.get("confidence_score"),
                            "execution_time_ms": row.get("execution_time_ms"),
                            "rows_affected": row.get("rows_affected"),
                            "status": row.get("status"),
                        },
                    )
                )
            return result
        finally:
            cursor.close()

    def _transaction_timeline(self, transaction_id: int, offset: int) -> list[InvestigationTimelineEntry]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT operation_id, operation_type, data_item, sequence_no, timestamp
                FROM transaction_operations
                WHERE transaction_id = %s
                ORDER BY sequence_no, operation_id
                """,
                (transaction_id,),
            )
            result = [
                InvestigationTimelineEntry(
                    sequence=offset + index,
                    source="transaction_operation",
                    source_id=row["operation_id"],
                    timestamp=row.get("timestamp"),
                    event_type=row["operation_type"],
                    description=f"{row['operation_type']} {row.get('data_item') or ''}".strip(),
                    payload=row,
                )
                for index, row in enumerate(cursor.fetchall(), 1)
            ]
            cursor.execute(
                """
                SELECT lock_id, data_item, lock_type, status, acquired_at, released_at
                FROM locks
                WHERE transaction_id = %s
                ORDER BY lock_id
                """,
                (transaction_id,),
            )
            start = offset + len(result)
            result.extend(
                InvestigationTimelineEntry(
                    sequence=start + index,
                    source="lock",
                    source_id=row["lock_id"],
                    timestamp=row.get("acquired_at") or row.get("released_at"),
                    event_type=f"LOCK_{row['status']}",
                    description=f"{row['lock_type']} lock on {row['data_item']}",
                    payload=row,
                )
                for index, row in enumerate(cursor.fetchall(), 1)
            )
            return result
        finally:
            cursor.close()

    def _performance(self, trace_id: int | None) -> list[PerformanceRecord]:
        if trace_id is None:
            return []
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT record_id, trace_id, metric_name, metric_value, data_source, recorded_at
                FROM performance_records
                WHERE trace_id = %s
                ORDER BY recorded_at, record_id
                """,
                (trace_id,),
            )
            return [PerformanceRecord(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()
