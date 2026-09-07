"""Rule-based cross-layer correlation service.

This module deliberately has no database, web, AI, or machine-learning
dependency.  It only validates identifiers and orders already-normalized
events.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from app.models.correlation import (
    CorrelationInput,
    CorrelationResult,
    CrossLayerTrace,
    EventCorrelation,
)


class CorrelationService:
    """Correlate OS events with one transaction/query context.

    A correlation is produced only when every candidate has the same positive
    PID, transaction ID, and query ID.  Events are then ordered by timestamp
    and OS event ID, making repeated runs deterministic.
    """

    METHOD = "PID_TRANSACTION_QUERY_TIMESTAMP_ORDER"
    STATUS = "CORRELATED"

    def __init__(self, trace_id: int | None = None) -> None:
        """Optionally accept a persistence-provided trace ID."""

        self.trace_id = trace_id

    def correlate(
        self,
        events: Iterable[CorrelationInput | Mapping[str, Any]],
    ) -> CorrelationResult:
        """Return a trace and causal sequence when the identifiers are valid.

        Invalid relationships return an empty result with a reason.  This is
        safer for an ingestion pipeline than inventing a causal relationship.
        Malformed individual inputs still raise Pydantic ``ValidationError``.
        """

        normalized = [
            event
            if isinstance(event, CorrelationInput)
            else CorrelationInput.model_validate(event)
            for event in events
        ]

        if not normalized:
            return self._empty_result("no events were supplied")

        duplicate_ids = len({event.os_event_id for event in normalized}) != len(
            normalized
        )
        if duplicate_ids:
            return self._empty_result("OS event IDs must be unique")

        first = normalized[0]
        if any(event.pid != first.pid for event in normalized):
            return self._empty_result("PID values do not match")

        if any(event.transaction_id is None for event in normalized):
            return self._empty_result("transaction ID is required for correlation")
        if any(event.query_id is None for event in normalized):
            return self._empty_result("query ID is required for correlation")

        if any(event.transaction_id != first.transaction_id for event in normalized):
            return self._empty_result("transaction IDs do not match")
        if any(event.query_id != first.query_id for event in normalized):
            return self._empty_result("query IDs do not match")

        ordered = sorted(
            normalized,
            key=lambda event: (event.timestamp, event.os_event_id),
        )
        trace = CrossLayerTrace(
            trace_id=self.trace_id,
            pid=first.pid,
            transaction_id=first.transaction_id,
            status=self.STATUS,
            started_at=ordered[0].timestamp,
            ended_at=ordered[-1].timestamp,
            summary=(
                f"PID {first.pid} correlated to transaction "
                f"{first.transaction_id} and query {first.query_id}"
            ),
        )
        correlations = [
            EventCorrelation(
                trace_id=self.trace_id,
                os_event_id=event.os_event_id,
                db_event_id=None,
                query_id=event.query_id,
                correlation_method=self.METHOD,
                confidence_score=1.0,
                sequence_order=sequence_order,
            )
            for sequence_order, event in enumerate(ordered, start=1)
        ]
        return CorrelationResult(trace=trace, correlations=correlations)

    def correlate_sequence(
        self,
        events: Iterable[CorrelationInput | Mapping[str, Any]],
    ) -> list[EventCorrelation]:
        """Convenience interface returning only the causal sequence."""

        return self.correlate(events).causal_sequence

    def _empty_result(self, reason: str) -> CorrelationResult:
        return CorrelationResult(reason=reason)
