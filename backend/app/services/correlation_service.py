"""Rule-based cross-layer correlation service.

This module deliberately has no database, web, AI, or machine-learning
dependency.  It only validates identifiers and orders already-normalized
events.

OS Live Reality Mode rules enforced here
-----------------------------------------
PID recycling
    PIDs are reused by the OS.  When ``process_start_time`` and
    ``process_stop_time`` are provided on a ``CorrelationInput``, the service
    verifies that the event's ``timestamp`` falls strictly within that window
    before accepting the PID as evidence.  A PID alone is never sufficient.

Null PIDs (filesystem events)
    Filesystem events intentionally carry ``pid=None``.  The service handles
    these via a time-window + ``file_path`` path rather than PID matching,
    and classifies the result as TEMPORAL rather than DIRECT.

Evidence completeness
    The ``evidence_completeness`` field from the OS collector (e.g. "4/5")
    counts satisfied deterministic checks; it is not a probability.  It is
    forwarded verbatim into ``CorrelationResult`` for transparency.

Host guard
    Events from different ``host_id`` values must not be correlated.
"""

from collections.abc import Iterable
from typing import Any

from app.models.correlation import (
    CorrelationInput,
    CorrelationResult,
    CrossLayerTrace,
    EventCorrelation,
)
from app.models.correlation_classification import CorrelationClassification
from app.services.evidence_service import EvidenceService


class CorrelationService:
    """Correlate OS events with one transaction/query context.

    A DIRECT correlation is produced only when every candidate has the same
    positive PID (which passes the recycling guard), transaction ID, and query
    ID.  Events are then ordered by timestamp and OS event ID, making repeated
    runs deterministic.

    A TEMPORAL correlation is produced for null-PID (filesystem) events when
    a common file_path and host_id are present and the timestamps fall within
    a 60-second window.
    """

    METHOD = "PID_TRANSACTION_QUERY_TIMESTAMP_ORDER"
    FILESYSTEM_METHOD = "FILE_PATH_HOST_TIMESTAMP_WINDOW"
    STATUS = "CORRELATED"

    def __init__(self, trace_id: int | None = None) -> None:
        """Optionally accept a persistence-provided trace ID."""

        self.trace_id = trace_id

    def correlate(
        self,
        events: Iterable[CorrelationInput | dict[str, Any]],
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

        evidence = EvidenceService().evaluate(normalized)

        if not normalized:
            return self._empty_result("no events were supplied", evidence)

        # ----- Duplicate event ID guard -----
        if len({event.os_event_id for event in normalized}) != len(normalized):
            return self._empty_result("OS event IDs must be unique", evidence)

        # ----- Host guard -----
        # Events from different hosts must never be correlated.
        host_ids = {event.host_id for event in normalized if event.host_id}
        if len(host_ids) > 1:
            return self._empty_result(
                "host_id values do not match; cross-host correlation is not permitted",
                evidence,
            )

        # ----- Null-PID filesystem path -----
        all_null_pid = all(event.pid is None for event in normalized)
        if all_null_pid:
            return self._correlate_filesystem(normalized, evidence)

        # Mixed null/non-null PIDs are not correlatable.
        if any(event.pid is None for event in normalized):
            return self._empty_result(
                "mixed null and non-null PIDs; cannot correlate filesystem and process "
                "events in the same call",
                evidence,
            )

        # ----- PID recycling guard -----
        first = normalized[0]
        if any(event.pid != first.pid for event in normalized):
            return self._empty_result("PID values do not match", evidence)

        for event in normalized:
            # Normalize process window timestamps to UTC-naive for comparison
            # (event.timestamp is UTC-naive after _normalize_timestamp runs).
            def _to_naive(dt):
                if dt is None:
                    return None
                if dt.tzinfo is not None:
                    from datetime import timezone as _tz
                    return dt.astimezone(_tz.utc).replace(tzinfo=None)
                return dt

            t_start = _to_naive(event.process_start_time)
            t_stop = _to_naive(event.process_stop_time)

            if t_start is not None and event.timestamp < t_start:
                return self._empty_result(
                    f"event timestamp {event.timestamp} precedes the observed "
                    f"process start time {t_start} for PID "
                    f"{event.pid}; possible PID recycling",
                    evidence,
                )
            if t_stop is not None and event.timestamp > t_stop:
                return self._empty_result(
                    f"event timestamp {event.timestamp} is after the observed "
                    f"process stop time {t_stop} for PID "
                    f"{event.pid}; possible PID recycling",
                    evidence,
                )


        # ----- DBMS identity guard -----
        if any(event.transaction_id is None for event in normalized):
            return self._empty_result(
                "transaction ID is required for correlation", evidence
            )
        if any(event.query_id is None for event in normalized):
            return self._empty_result("query ID is required for correlation", evidence)

        if any(event.transaction_id != first.transaction_id for event in normalized):
            return self._empty_result("transaction IDs do not match", evidence)
        if any(event.query_id != first.query_id for event in normalized):
            return self._empty_result("query IDs do not match", evidence)

        # ----- Build DIRECT result -----
        ordered = sorted(
            normalized,
            key=lambda event: (event.timestamp, event.os_event_id),
        )
        trace = CrossLayerTrace(
            trace_id=self.trace_id,
            pid=first.pid,
            transaction_id=first.transaction_id,
            host_id=first.host_id,
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
                sequence_order=sequence_order,
            )
            for sequence_order, event in enumerate(ordered, start=1)
        ]

        # Forward the OS collector's own evidence completeness string.
        os_evidence_completeness = self._extract_evidence_completeness(normalized)

        return CorrelationResult(
            trace=trace,
            correlations=correlations,
            classification=CorrelationClassification.DIRECT,
            evidence_score=evidence,
            evidence_summary=evidence.to_summary(),
            os_evidence_completeness=os_evidence_completeness,
        )

    def _correlate_filesystem(
        self,
        normalized: list[CorrelationInput],
        evidence,
    ) -> "CorrelationResult":
        """Attempt a TEMPORAL correlation for null-PID filesystem events.

        Requires:
        - All events share the same ``host_id``.
        - All events share the same non-empty ``file_path``.
        - All events fall within a 60-second time window.
        """
        first = normalized[0]

        # file_path context is required for filesystem correlation.
        file_paths = {event.file_path for event in normalized}
        if None in file_paths or len(file_paths) != 1:
            return self._empty_result(
                "null-PID filesystem correlation requires a unique, shared file_path",
                evidence,
            )

        ordered = sorted(
            normalized,
            key=lambda event: (event.timestamp, event.os_event_id),
        )
        time_diff = (ordered[-1].timestamp - ordered[0].timestamp).total_seconds()
        if time_diff >= 60.0:
            return self._empty_result(
                "null-PID filesystem events span more than 60 seconds; "
                "cannot establish a temporal correlation window",
                evidence,
            )

        trace = CrossLayerTrace(
            trace_id=self.trace_id,
            pid=None,
            host_id=first.host_id,
            status=self.STATUS,
            started_at=ordered[0].timestamp,
            ended_at=ordered[-1].timestamp,
            summary=(
                f"Filesystem path '{first.file_path}' correlated via time window "
                f"on host '{first.host_id}'"
            ),
        )
        correlations = [
            EventCorrelation(
                trace_id=self.trace_id,
                os_event_id=event.os_event_id,
                db_event_id=None,
                query_id=event.query_id,
                correlation_method=self.FILESYSTEM_METHOD,
                sequence_order=seq,
            )
            for seq, event in enumerate(ordered, start=1)
        ]
        os_evidence_completeness = self._extract_evidence_completeness(normalized)
        return CorrelationResult(
            trace=trace,
            correlations=correlations,
            classification=CorrelationClassification.TEMPORAL,
            evidence_score=evidence,
            evidence_summary=evidence.to_summary(),
            os_evidence_completeness=os_evidence_completeness,
        )

    def correlate_sequence(
        self,
        events: Iterable[CorrelationInput | dict[str, Any]],
    ) -> list[EventCorrelation]:
        """Convenience interface returning only the causal sequence."""

        return self.correlate(events).causal_sequence

    def _empty_result(self, reason: str, evidence=None) -> CorrelationResult:
        classification = CorrelationClassification.NONE

        # If timestamps are close, but we failed identity matching, classify as temporal.
        if evidence and evidence.timestamp_relation and not evidence.transaction_match:
            classification = CorrelationClassification.TEMPORAL

        summary = evidence.to_summary() if evidence else None

        return CorrelationResult(
            reason=reason,
            classification=classification,
            evidence_score=evidence,
            evidence_summary=summary,
        )

    @staticmethod
    def _extract_evidence_completeness(
        events: list[CorrelationInput],
    ) -> str | None:
        """Return the first non-None evidence_completeness value from the OS events."""
        for event in events:
            if event.evidence_completeness:
                return event.evidence_completeness
        return None
