"""
Tests for the backend foundation milestone:
- health check
- valid event ingestion
- retrieving a stored event
- invalid pid rejection
- invalid event_type rejection
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.event_service import event_service


@pytest.fixture(autouse=True)
def reset_event_store():
    """Each test starts with a clean in-memory store and ID counter."""
    event_service._events.clear()
    event_service._next_id = 1
    yield


@pytest.fixture
def client():
    return TestClient(app)


VALID_EVENT = {
    "timestamp": "2026-08-26T10:15:03.221+00:00",
    "pid": 4211,
    "ppid": 1,
    "user": "krishna",
    "event_type": "process_created",
    "file_path": "/usr/bin/python3",
}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_valid_event(client):
    response = client.post("/api/events", json=VALID_EVENT)
    assert response.status_code == 201
    body = response.json()
    assert body["pid"] == VALID_EVENT["pid"]
    assert body["event_type"] == VALID_EVENT["event_type"]
    assert body["id"] == 1
    assert "received_at" in body


def test_retrieve_ingested_event(client):
    client.post("/api/events", json=VALID_EVENT)
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["pid"] == VALID_EVENT["pid"]


def test_retrieve_events_most_recent_first(client):
    first = {**VALID_EVENT, "pid": 100}
    second = {**VALID_EVENT, "pid": 200}
    client.post("/api/events", json=first)
    client.post("/api/events", json=second)

    response = client.get("/api/events")
    events = response.json()
    assert [e["pid"] for e in events] == [200, 100]


def test_retrieve_events_respects_limit(client):
    for pid in range(1, 6):
        client.post("/api/events", json={**VALID_EVENT, "pid": pid})

    response = client.get("/api/events", params={"limit": 2})
    events = response.json()
    assert len(events) == 2
    assert [e["pid"] for e in events] == [5, 4]


def test_reject_invalid_pid(client):
    bad_event = {**VALID_EVENT, "pid": -1}
    response = client.post("/api/events", json=bad_event)
    assert response.status_code == 422


def test_reject_zero_pid(client):
    bad_event = {**VALID_EVENT, "pid": 0}
    response = client.post("/api/events", json=bad_event)
    assert response.status_code == 422


def test_reject_invalid_event_type(client):
    bad_event = {**VALID_EVENT, "event_type": "file_deleted"}
    response = client.post("/api/events", json=bad_event)
    assert response.status_code == 422


def test_reject_missing_required_field(client):
    bad_event = {k: v for k, v in VALID_EVENT.items() if k != "pid"}
    response = client.post("/api/events", json=bad_event)
    assert response.status_code == 422


def test_null_file_path_is_accepted(client):
    event = {**VALID_EVENT, "file_path": None}
    response = client.post("/api/events", json=event)
    assert response.status_code == 201
    assert response.json()["file_path"] is None
