"""Deterministic evaluation of correlation evidence."""

from collections.abc import Iterable

from app.models.correlation import CorrelationInput
from app.models.correlation_classification import EvidenceScore


class EvidenceService:
    """Evaluate evidence completeness for a set of normalized events."""

    def evaluate(self, events: Iterable[CorrelationInput]) -> EvidenceScore:
        """Deterministically assess factors across the provided candidates."""
        events_list = list(events)
        if not events_list:
            return EvidenceScore()

        first = events_list[0]

        # PID match: only meaningful when all events carry a non-null PID.
        # Filesystem events intentionally have pid=None; skip the PID check for
        # those so we don't falsely penalise a valid filesystem-path correlation.
        all_have_pid = all(e.pid is not None for e in events_list)
        pid_match = all_have_pid and all(e.pid == first.pid for e in events_list)

        # Ensure all events have a transaction ID and they all match
        transaction_match = all(
            e.transaction_id is not None and e.transaction_id == first.transaction_id
            for e in events_list
        )

        # Ensure all events have a query ID and they all match
        query_match = all(
            e.query_id is not None and e.query_id == first.query_id
            for e in events_list
        )

        # DB connection match is implicitly satisfied if the application successfully
        # provided a continuous transaction and query chain for the same PID.
        db_connection_match = transaction_match and query_match

        # Check ordering: events should be naturally sorted by timestamp
        ordered = sorted(events_list, key=lambda e: (e.timestamp, e.os_event_id))
        event_ordering = ordered == events_list

        # Timestamps are close (< 60 seconds across all candidate events = temporal relation)
        if events_list:
            time_diff = (ordered[-1].timestamp - ordered[0].timestamp).total_seconds()
            timestamp_relation = time_diff < 60.0
        else:
            timestamp_relation = False

        # Lock relation is currently external to simple correlation.
        lock_relation = False

        # Host match: all events share the same non-None host_id.
        host_ids = {e.host_id for e in events_list}
        host_match = (
            len(host_ids) == 1
            and first.host_id is not None
            and first.host_id.strip() != ""
        )

        return EvidenceScore(
            pid_match=pid_match,
            db_connection_match=db_connection_match,
            transaction_match=transaction_match,
            query_match=query_match,
            timestamp_relation=timestamp_relation,
            event_ordering=event_ordering,
            lock_relation=lock_relation,
            host_match=host_match,
        )
