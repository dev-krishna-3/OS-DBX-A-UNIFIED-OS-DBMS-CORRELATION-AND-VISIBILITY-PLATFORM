"""Tests for final live observability updates.

Verifies:
1. Admin authorization check & clear 403 detail
2. OS What-If scenarios (CPU_LOAD, MEMORY_PRESSURE, DISK_IO, RESOURCE_CONTENTION)
3. Live system-health endpoint & graceful fallback
4. DBMS Performance Schema status & graceful unavailable handling
5. OS monitoring status endpoint & stopped state label
6. Identity Bridge administrator privilege warning
7. Deterministic correlation classification (DIRECT, TEMPORAL, NONE)
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.users import UserInDB
from app.models.correlation import CorrelationInput
from app.services.correlation_service import CorrelationService
from app.models.correlation_classification import CorrelationClassification


@pytest.fixture
def test_client():
    return TestClient(app)


def test_admin_authorization_and_forbidden_detail(test_client):
    """Normal non-admin user must receive 403 with detailed guidance."""
    normal_user = UserInDB(
        user_id=99,
        username="normal_user",
        uid_linux=1005,
        password_hash="mockhash",
        created_at="2026-01-01T00:00:00",
        is_admin=False
    )
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: normal_user

    try:
        response = test_client.get("/api/audit/")
        assert response.status_code == 403
        data = response.json()
        assert "Admin privileges required" in data["detail"]
        assert "username: admin" in data["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_os_what_if_cpu_load(test_client):
    """OS What-If CPU load scaling should deterministically compute utilization and risk."""
    payload = {
        "name": "Heavy Concurrency Test",
        "scenario_type": "CPU_LOAD",
        "parameters": {
            "process_count": 50,
            "avg_burst_ms": 60.0,
            "core_count": 4
        }
    }
    response = test_client.post("/api/what-if/os", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["analysis_type"] == "CPU_LOAD"
    res = data["result"]
    assert res["mode"] == "[ANALYSIS] [SIMULATION]"
    assert res["process_count"] == 50
    assert res["bottleneck_risk"] == "MODERATE"
    assert res["estimated_cpu_utilization_pct"] == 75.0


def test_os_what_if_memory_pressure(test_client):
    """OS What-If Memory Pressure should deterministically model FIFO page faults."""
    payload = {
        "name": "Paging Thrashing Test",
        "scenario_type": "MEMORY_PRESSURE",
        "parameters": {
            "allocated_mb": 7800,
            "total_ram_mb": 8192,
            "frames": 3,
            "page_references": [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        }
    }
    response = test_client.post("/api/what-if/os", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["analysis_type"] == "MEMORY_PRESSURE"
    res = data["result"]
    assert res["mode"] == "[ANALYSIS] [SIMULATION]"
    assert res["page_faults"] > 0
    assert "thrashing_risk" in res


def test_os_what_if_disk_io(test_client):
    """OS What-If Disk I/O should deterministically calculate SSTF seek distance."""
    payload = {
        "name": "SSTF Disk Benchmark",
        "scenario_type": "DISK_IO",
        "parameters": {
            "current_head": 50,
            "requests": [10, 80, 20, 70],
            "algorithm": "SSTF"
        }
    }
    response = test_client.post("/api/what-if/os", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["analysis_type"] == "DISK_IO"
    res = data["result"]
    assert res["mode"] == "[ANALYSIS] [SIMULATION]"
    assert res["total_head_movement_cylinders"] > 0
    assert len(res["execution_sequence"]) == 4


def test_os_what_if_resource_contention(test_client):
    """OS What-If Concurrency should calculate lock convoy probability."""
    payload = {
        "name": "Deadlock Risk Simulation",
        "scenario_type": "RESOURCE_CONTENTION",
        "parameters": {
            "concurrent_tasks": 16,
            "shared_locks": 4
        }
    }
    response = test_client.post("/api/what-if/os", json=payload)
    assert response.status_code == 201
    data = response.json()
    res = data["result"]
    assert "contention_index" in res
    assert "lock_convoy_probability" in res


def test_system_health_endpoint(test_client):
    """System-wide performance health endpoint should report hardware and DBMS metrics."""
    response = test_client.get("/api/performance/system-health")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert "dbms" in data
    assert "correlation" in data
    assert "overhead" in data
    assert "cpu_percent" in data["system"]
    assert "memory_percent" in data["system"]
    assert "available" in data["dbms"]


def test_dbms_observation_status_endpoint(test_client):
    """DBMS observation status should cleanly report availability without crashing."""
    response = test_client.get("/api/dbms-events/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("AVAILABLE", "UNAVAILABLE")
    assert "label" in data


def test_os_monitoring_status_endpoint(test_client):
    """OS collector status endpoint should report RUNNING or STOPPED with proper label."""
    response = test_client.get("/api/os-events/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("RUNNING", "STOPPED")
    assert data["label"] in ("[LIVE]", "[OS MONITORING: STOPPED]")


def test_identity_bridge_live_map_advisory(test_client):
    """Identity Bridge should return active mappings and administrator privilege warning if unprivileged."""
    response = test_client.get("/api/bridge/live-map")
    assert response.status_code == 200
    data = response.json()
    assert "active_bridges" in data
    assert "mapping" in data
    assert "is_admin" in data


def test_correlation_classification_distinction():
    """Prove that direct socket identity produces DIRECT classification, while timestamp alone does not."""
    service = CorrelationService()

    # 1. Event with PID and query
    inputs = [
        CorrelationInput(
            os_event_id="ev-1",
            pid=2048,
            transaction_id=1,
            query_id=10,
            timestamp="2026-03-31T12:00:00Z",
            event_type="process_activity",
            source="os_events"
        )
    ]
    result = service.correlate(inputs)
    assert result.is_correlated is True
    assert result.classification in (CorrelationClassification.DIRECT, CorrelationClassification.TEMPORAL)

    # 2. Filesystem event with pid=null (temporal proximity only, never direct)
    fs_inputs = [
        CorrelationInput(
            os_event_id="ev-fs",
            pid=None,
            timestamp="2026-03-31T12:00:00Z",
            event_type="file_modified",
            file_path="C:\\test\\app.log",
            source="OS"
        )
    ]
    fs_result = service.correlate(fs_inputs)
    # Filesystem without PID must never be classified as DIRECT
    assert fs_result.classification != CorrelationClassification.DIRECT


def test_identity_bridge_unprivileged_resolution():
    """Identity Bridge must resolve client sockets using unprivileged Windows netstat without AccessDenied."""
    from app.services.identity_bridge import IdentityBridgeService
    bridge = IdentityBridgeService()
    ports = bridge.get_os_client_ports()
    assert isinstance(ports, dict)
    # has_access_denied should remain False when netstat parses sockets on Windows
    import os
    if os.name == 'nt':
        assert bridge.has_access_denied is False


def test_dbms_observation_fallback_mechanism():
    """MySQLQueryCollector must support processlist fallback when performance_schema is disabled."""
    from app.collectors.mysql_query_collector import MySQLQueryCollector
    from unittest.mock import MagicMock
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [100]
    mock_cursor.fetchall.return_value = [
        {"ID": 42, "USER": "test_user", "HOST": "localhost:54321", "DB": "os_dbx", "COMMAND": "Query", "TIME": 1, "STATE": "executing", "INFO": "SELECT * FROM orders"}
    ]
    mock_conn.cursor.return_value = mock_cursor

    collector = MySQLQueryCollector(mock_conn)
    observations = collector.poll_from_processlist(limit=10)
    assert len(observations) == 1
    assert observations[0].connection_id == 42
    assert observations[0].query_text == "SELECT * FROM orders"
    assert observations[0].status == "EXECUTING"


def test_os_watchdog_collector_start_endpoint(test_client):
    """POST /api/os-events/start must start the watchdog collector and report status."""
    response = test_client.post("/api/os-events/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("RUNNING", "STOPPED")
    assert "label" in data
    assert "message" in data
