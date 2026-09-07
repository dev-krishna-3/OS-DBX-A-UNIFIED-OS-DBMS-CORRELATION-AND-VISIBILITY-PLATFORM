"""Service layer for recording DBMS query executions."""

from datetime import datetime, timezone
from typing import Protocol

from app.models.events import DBMSEvent
from app.models.query_executions import (
    QueryExecutionRecord,
    QueryExecutionRequest,
)


def utc_now() -> datetime:
    """Return the current UTC time in MySQL DATETIME-compatible form."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class QueryRepositoryProtocol(Protocol):
    """Minimal repository interface needed by ``QueryService``."""

    def record_query(self, event: DBMSEvent) -> int:
        ...


class QueryService:
    """Build normalized events and ask a repository to persist them."""

    def __init__(self, repository: QueryRepositoryProtocol) -> None:
        self.repository = repository

    def record_query(
        self, request: QueryExecutionRequest
    ) -> QueryExecutionRecord:
        """Record a request and return it with the database query ID."""

        event = DBMSEvent(
            transaction_id=request.transaction_id,
            pid=request.pid,
            query_type=request.query_type,
            query_text=request.query_text,
            execution_time_ms=request.execution_time_ms,
            rows_affected=request.rows_affected,
            status=request.status,
            timestamp=request.timestamp or utc_now(),
        )

        query_id = self.repository.record_query(event)
        event_values = event.model_dump(exclude={"query_id"})

        return QueryExecutionRecord(
            query_id=query_id,
            **event_values,
        )

    record_execution = record_query
