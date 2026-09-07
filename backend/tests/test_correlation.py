"""Tests for deterministic cross-layer correlation."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.correlation import CorrelationInput
from app.services.correlation_service import CorrelationService


BASE_TIME = datetime(2026, 9, 7, 10, 0, 0)


def event(
    os_event_id: int,
    offset_seconds: int,
    *,
    pid: int = 4211,
    transaction_id: int | None = 12,
    query_id: int | None = 25,
    event_type: str = "PROCESS_QUERY",
    source: str = "OS",
) -> CorrelationInput:
    return CorrelationInput(
        os_event_id=os_event_id,
        pid=pid,
        transaction_id=transaction_id,
        query_id=query_id,
        timestamp=BASE_TIME + timedelta(seconds=offset_seconds),
        event_type=event_type,
        source=source,
    )


def test_valid_process_transaction_query_correlation():
    result = CorrelationService(trace_id=7).correlate(
        [
            event(3, 2, event_type="QUERY"),
            event(1, 0, event_type="PROCESS"),
            event(2, 1, event_type="TRANSACTION"),
        ]
    )

    assert result.is_correlated
    assert result.trace.trace_id == 7
    assert result.trace.pid == 4211
    assert result.trace.transaction_id == 12
    assert [item.os_event_id for item in result.causal_sequence] == [1, 2, 3]
    assert [item.sequence_order for item in result.correlations] == [1, 2, 3]
    assert all(item.query_id == 25 for item in result.correlations)
    assert all(item.confidence_score == 1.0 for item in result.correlations)


def test_pid_mismatch_does_not_claim_causation():
    result = CorrelationService().correlate([event(1, 0), event(2, 1, pid=9999)])

    assert not result.is_correlated
    assert result.trace is None
    assert result.correlations == []
    assert result.reason == "PID values do not match"


def test_missing_transaction_does_not_claim_causation():
    result = CorrelationService().correlate(
        [event(1, 0, transaction_id=None), event(2, 1, transaction_id=None)]
    )

    assert not result.is_correlated
    assert result.reason == "transaction ID is required for correlation"


def test_missing_query_does_not_claim_causation():
    result = CorrelationService().correlate(
        [event(1, 0, query_id=None), event(2, 1, query_id=None)]
    )

    assert not result.is_correlated
    assert result.reason == "query ID is required for correlation"


def test_timestamp_and_event_id_define_sequence_order():
    result = CorrelationService().correlate(
        [
            event(20, 2),
            event(10, 1),
            event(30, 1),
        ]
    )

    # At the same timestamp, the event ID is the stable tie-breaker.
    assert [item.os_event_id for item in result.causal_sequence] == [10, 30, 20]
    assert result.trace.started_at == BASE_TIME + timedelta(seconds=1)
    assert result.trace.ended_at == BASE_TIME + timedelta(seconds=2)


def test_repeated_runs_are_deterministic():
    inputs = [event(3, 2), event(1, 0), event(2, 1)]
    service = CorrelationService(trace_id=7)

    first = service.correlate(inputs).model_dump()
    second = service.correlate(inputs).model_dump()

    assert first == second


@pytest.mark.parametrize(
    "field,value",
    [
        ("os_event_id", 0),
        ("pid", 0),
        ("event_type", " "),
        ("source", ""),
        ("timestamp", "not-a-timestamp"),
    ],
)
def test_invalid_correlation_input_is_rejected(field, value):
    values = event(1, 0).model_dump()

    with pytest.raises(ValidationError):
        CorrelationInput(**{**values, field: value})


def test_aware_timestamps_are_normalized_to_utc():
    normalized = CorrelationInput(
        **event(1, 0).model_dump(
            exclude={"timestamp"}
        ),
        timestamp=datetime(2026, 9, 7, 15, 30, tzinfo=timezone.utc),
    )

    assert normalized.timestamp == datetime(2026, 9, 7, 15, 30)
    assert normalized.timestamp.tzinfo is None
