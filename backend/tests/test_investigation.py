"""Validation for trace-backed incident replay."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.routes_investigation import get_investigation_repository
from app.main import app
from app.models.deadlocks import IncidentRecord
from app.models.investigation import IncidentInvestigation, InvestigationTimelineEntry
from app.repositories.investigation_repository import (
    InvestigationRepository,
    ReplayUnavailableError,
)


INCIDENT = IncidentRecord(
    incident_id=41,
    trace_id=None,
    incident_type="DEADLOCK",
    detected_at=datetime(2026, 10, 3, 12, 0),
    resolved=False,
)


class NoDatabaseAccess:
    def cursor(self, *args, **kwargs):
        raise AssertionError("invalid replay must be rejected before database access")


def test_replay_requires_linked_trace():
    investigation = IncidentInvestigation(incident=INCIDENT)

    with pytest.raises(ReplayUnavailableError, match="no linked cross-layer trace"):
        InvestigationRepository(NoDatabaseAccess()).save_replay(investigation)


def test_replay_requires_correlated_events():
    investigation = IncidentInvestigation(
        incident=INCIDENT.model_copy(update={"trace_id": 7}),
        trace={"trace_id": 7},
        timeline=[
            InvestigationTimelineEntry(
                sequence=1,
                source="trace",
                source_id=7,
                event_type="TRACE_STARTED",
                description="trace began",
            )
        ],
    )

    with pytest.raises(ReplayUnavailableError, match="no correlated events"):
        InvestigationRepository(NoDatabaseAccess()).save_replay(investigation)


def test_replay_api_returns_actionable_conflict_for_missing_trace():
    class FakeRepository:
        def investigate(self, incident_id):
            return IncidentInvestigation(incident=INCIDENT)

        def save_replay(self, investigation):
            return InvestigationRepository(NoDatabaseAccess()).save_replay(investigation)

    app.dependency_overrides[get_investigation_repository] = lambda: FakeRepository()
    try:
        response = TestClient(app).post("/api/incidents/41/replay")
    finally:
        app.dependency_overrides.pop(get_investigation_repository, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "No cross-layer trace available — replay cannot be performed."


def test_replay_api_succeeds_with_valid_trace():
    valid_incident = INCIDENT.model_copy(update={"trace_id": 101})
    investigation = IncidentInvestigation(
        incident=valid_incident,
        trace={"trace_id": 101, "status": "CORRELATED"},
        timeline=[
            InvestigationTimelineEntry(
                sequence=1,
                source="trace",
                source_id=101,
                event_type="TRACE_STARTED",
                description="trace began",
            ),
            InvestigationTimelineEntry(
                sequence=2,
                source="correlation",
                source_id=1,
                event_type="CORRELATION",
                description="correlated event",
            ),
        ],
    )

    class FakeSuccessRepository:
        def investigate(self, incident_id):
            return investigation

        def save_replay(self, inv):
            from app.models.investigation import IncidentReplay
            return IncidentReplay(
                replay_id=99,
                incident_id=inv.incident.incident_id,
                replayed_at=datetime(2026, 10, 3, 12, 5),
                outcome="REPLAYED",
                steps=inv.timeline,
                summary="Replay simulated successfully",
            )

    app.dependency_overrides[get_investigation_repository] = lambda: FakeSuccessRepository()
    try:
        response = TestClient(app).post("/api/incidents/41/replay")
    finally:
        app.dependency_overrides.pop(get_investigation_repository, None)

    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "REPLAYED"
    assert data["replay_id"] == 99
    assert len(data["steps"]) == 2

