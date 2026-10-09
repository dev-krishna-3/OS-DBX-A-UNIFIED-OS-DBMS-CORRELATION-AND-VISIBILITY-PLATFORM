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
    assert response.json()["detail"] == "Incident has no linked cross-layer trace"
