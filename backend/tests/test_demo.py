"""Smoke tests for the evaluator-friendly FastAPI demonstration surface."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_details_reports_correlation_engine_ready():
    response = client.get("/health/details")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["correlation_engine"] == "ready"


def test_correlation_demo_runs_without_database():
    response = client.get("/api/demo/correlation")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PASS"
    assert body["result"]["trace"]["status"] == "CORRELATED"
    assert [item["os_event_id"] for item in body["result"]["correlations"]] == [
        1001,
        1002,
        1003,
    ]
    assert all(check["passed"] for check in body["checks"])


def test_openapi_publishes_health_and_demo_paths():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/health" in paths
    assert "/health/details" in paths
    assert "/api/demo/correlation" in paths
