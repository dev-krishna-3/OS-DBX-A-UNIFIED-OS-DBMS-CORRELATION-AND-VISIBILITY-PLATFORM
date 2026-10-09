"""Tests for the OS Live Reality Mode integration contract.

Covers the five new behaviours introduced by the contract:
1. Filesystem events with pid=null are accepted at the dedicated endpoint.
2. PID recycling guard rejects events outside the process lifetime window.
3. Filesystem (null-PID) events receive a TEMPORAL classification, not DIRECT.
4. evidence_completeness from the OS event is forwarded into CorrelationResult.
5. /health/details includes os_stream_metrics (even when adapter is absent).
"""

from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.correlation import CorrelationInput
from app.models.events import OSFilesystemEvent, OSEvent, OSEventType
from app.models.correlation_classification import CorrelationClassification
from app.services.correlation_service import CorrelationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(offset_seconds: float = 0.0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)


def _make_process_input(**kwargs) -> CorrelationInput:
    defaults = dict(
        os_event_id="uuid-proc-1",
        pid=1234,
        transaction_id=10,
        query_id=5,
        timestamp=_utc(),
        event_type="process_created",
        source="OS",
        host_id="test-host",
    )
    defaults.update(kwargs)
    return CorrelationInput(**defaults)


def _make_filesystem_input(**kwargs) -> CorrelationInput:
    defaults = dict(
        os_event_id="uuid-fs-1",
        pid=None,
        timestamp=_utc(),
        event_type="file_modified",
        source="OS",
        host_id="test-host",
        file_path="C:\\temp\\sample.txt",
    )
    defaults.update(kwargs)
    return CorrelationInput(**defaults)


# ---------------------------------------------------------------------------
# 1. Filesystem event accepted with pid=null via dedicated endpoint
# ---------------------------------------------------------------------------

client = TestClient(app)


def test_null_pid_filesystem_event_accepted():
    """POST /api/os-events/filesystem must accept pid=null and return 201."""
    payload = {
        "event_id": "fs-event-uuid-001",
        "source": "OS",
        "timestamp": _utc().isoformat(),
        "event_type": "file_modified",
        "host_id": "test-host",
        "file_path": "C:\\temp\\test.txt",
        "pid": None,
    }
    response = client.post("/api/os-events/filesystem", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["pid"] is None
    assert body["event_id"] == "fs-event-uuid-001"
    assert body["host_id"] == "test-host"
    assert "id" in body
    assert "received_at" in body


def test_process_event_rejects_null_pid():
    """POST /api/os-events must reject pid=null (process events require a PID)."""
    payload = {
        "event_id": "proc-event-uuid-002",
        "source": "OS",
        "timestamp": _utc().isoformat(),
        "event_type": "process_created",
        "host_id": "test-host",
        "pid": None,
        "ppid": 0,
        "user": "testuser",
    }
    response = client.post("/api/os-events", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 2. PID recycling guard
# ---------------------------------------------------------------------------

def test_pid_recycling_guard_rejects_event_before_start():
    """Correlation must fail when the event precedes the process start time."""
    now = _utc()
    event = _make_process_input(
        timestamp=now - timedelta(seconds=10),  # before the process started
        process_start_time=now,
        process_stop_time=now + timedelta(seconds=30),
    )
    result = CorrelationService().correlate([event])
    assert not result.is_correlated
    assert result.reason is not None
    assert "PID" in result.reason or "timestamp" in result.reason.lower()


def test_pid_recycling_guard_rejects_event_after_stop():
    """Correlation must fail when the event is after the process stop time."""
    now = _utc()
    event = _make_process_input(
        timestamp=now + timedelta(seconds=60),  # long after process stopped
        process_start_time=now - timedelta(seconds=30),
        process_stop_time=now,
    )
    result = CorrelationService().correlate([event])
    assert not result.is_correlated
    assert result.reason is not None


def test_pid_recycling_guard_accepts_event_inside_window():
    """Correlation must succeed when the event timestamp is within the window."""
    now = _utc()
    event = _make_process_input(
        timestamp=now,
        process_start_time=now - timedelta(seconds=5),
        process_stop_time=now + timedelta(seconds=5),
    )
    result = CorrelationService().correlate([event])
    assert result.is_correlated
    assert result.classification == CorrelationClassification.DIRECT


# ---------------------------------------------------------------------------
# 3. Filesystem null-PID events receive TEMPORAL classification
# ---------------------------------------------------------------------------

def test_filesystem_event_gets_temporal_classification():
    """Null-PID filesystem events must be classified as TEMPORAL, not DIRECT."""
    e1 = _make_filesystem_input(os_event_id="uuid-fs-a", timestamp=_utc(0))
    e2 = _make_filesystem_input(os_event_id="uuid-fs-b", timestamp=_utc(5))
    result = CorrelationService().correlate([e1, e2])
    assert result.is_correlated
    assert result.classification == CorrelationClassification.TEMPORAL
    assert result.trace is not None
    assert result.trace.pid is None


def test_filesystem_event_without_file_path_not_correlated():
    """Null-PID events without a common file_path must not produce a trace."""
    e1 = _make_filesystem_input(os_event_id="uuid-fs-c", file_path=None)
    e2 = _make_filesystem_input(os_event_id="uuid-fs-d", file_path=None)
    result = CorrelationService().correlate([e1, e2])
    assert not result.is_correlated


def test_filesystem_event_beyond_60s_window_not_correlated():
    """Null-PID events spanning > 60 s must not produce a temporal correlation."""
    e1 = _make_filesystem_input(os_event_id="uuid-fs-e", timestamp=_utc(0))
    e2 = _make_filesystem_input(os_event_id="uuid-fs-f", timestamp=_utc(61))
    result = CorrelationService().correlate([e1, e2])
    assert not result.is_correlated


# ---------------------------------------------------------------------------
# 4. evidence_completeness forwarded from OS event
# ---------------------------------------------------------------------------

def test_evidence_completeness_field_forwarded():
    """os_evidence_completeness in CorrelationResult must reflect the OS event field."""
    now = _utc()
    event = _make_process_input(evidence_completeness="4/5")
    result = CorrelationService().correlate([event])
    assert result.is_correlated
    assert result.os_evidence_completeness == "4/5"


def test_evidence_completeness_none_when_not_provided():
    """os_evidence_completeness must be None when the OS event omits the field."""
    event = _make_process_input(evidence_completeness=None)
    result = CorrelationService().correlate([event])
    assert result.is_correlated
    assert result.os_evidence_completeness is None


# ---------------------------------------------------------------------------
# 5. /health/details includes os_stream_metrics
# ---------------------------------------------------------------------------

def test_health_details_includes_stream_metrics_key():
    """/health/details must always include os_stream_metrics (may be None if adapter absent)."""
    response = client.get("/health/details")
    assert response.status_code == 200
    body = response.json()
    assert "os_stream_metrics" in body
    # When the adapter is not installed, the value is None and a note is provided.
    if body["os_stream_metrics"] is None:
        assert "os_adapter_note" in body


def test_health_details_includes_adapter_health_key():
    """/health/details must always include os_adapter_health."""
    response = client.get("/health/details")
    assert response.status_code == 200
    body = response.json()
    assert "os_adapter_health" in body


# ---------------------------------------------------------------------------
# 6. Host guard
# ---------------------------------------------------------------------------

def test_cross_host_events_not_correlated():
    """Events from different host_ids must not be correlated."""
    e1 = _make_process_input(os_event_id="uuid-host-1", host_id="host-A")
    e2 = _make_process_input(os_event_id="uuid-host-2", host_id="host-B")
    result = CorrelationService().correlate([e1, e2])
    assert not result.is_correlated
    assert result.reason is not None
    assert "host" in result.reason.lower()


# ---------------------------------------------------------------------------
# 7. Mixed null/non-null PIDs rejected
# ---------------------------------------------------------------------------

def test_mixed_pid_and_null_pid_not_correlated():
    """Mixing a process event (pid set) with a filesystem event (pid=null) must fail."""
    proc = _make_process_input(os_event_id="uuid-mixed-1")
    fs = _make_filesystem_input(os_event_id="uuid-mixed-2")
    result = CorrelationService().correlate([proc, fs])
    assert not result.is_correlated
    assert result.reason is not None
