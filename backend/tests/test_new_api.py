from fastapi.testclient import TestClient

from app.main import app


def test_deadlock_api_returns_cycle():
    response = TestClient(app).post(
        "/api/deadlocks/detect",
        json={
            "locks": [
                {"transaction_id": 1, "data_item": "A", "lock_type": "X", "status": "HELD"},
                {"transaction_id": 2, "data_item": "B", "lock_type": "X", "status": "HELD"},
                {"transaction_id": 1, "data_item": "B", "lock_type": "X", "status": "WAITING"},
                {"transaction_id": 2, "data_item": "A", "lock_type": "X", "status": "WAITING"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["deadlock_detected"] is True


def test_recovery_api_returns_recovered_state():
    response = TestClient(app).post(
        "/api/recovery/recover",
        json={
            "initial_state": {"x": "0"},
            "logs": [
                {"sequence": 1, "transaction_id": 1, "log_type": "UPDATE", "data_item": "x", "old_value": "0", "new_value": "1"},
                {"sequence": 2, "transaction_id": 1, "log_type": "COMMIT"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["final_state"] == {"x": "1"}


def test_schedule_api_returns_non_serializable_for_cycle():
    response = TestClient(app).post(
        "/api/schedules/analyze",
        json={
            "operations": [
                {"transaction_id": 1, "operation": "W", "data_item": "A"},
                {"transaction_id": 2, "operation": "R", "data_item": "A"},
                {"transaction_id": 2, "operation": "W", "data_item": "B"},
                {"transaction_id": 1, "operation": "R", "data_item": "B"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["conflict_serializable"] is False
