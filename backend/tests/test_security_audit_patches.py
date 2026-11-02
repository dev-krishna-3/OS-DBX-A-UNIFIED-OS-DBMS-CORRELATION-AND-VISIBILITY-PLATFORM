"""Automated verification tests for security audit patches."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import require_admin
from app.models.users import UserInDB
from app.services.event_service import event_service
from app.api.routes_events import get_event_service
from datetime import datetime, timezone


@pytest.fixture
def client():
    return TestClient(app)


def override_require_admin():
    return UserInDB(
        user_id=1,
        username="admin",
        uid_linux=0,
        password_hash="",
        created_at=datetime(2026, 1, 1),
        is_admin=True,
    )


def test_cors_allows_workspace_id_header(client):
    """Verify that OPTIONS preflight allows the X-Workspace-ID header."""
    response = client.options(
        "/api/events",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type,x-workspace-id",
        },
    )
    assert response.status_code == 200
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-workspace-id" in allowed_headers


def test_sql_console_blocks_credentials_tables(client):
    """Verify SEC-02 fix: SQL console forbids querying sensitive tables."""
    app.dependency_overrides[require_admin] = override_require_admin
    try:
        sensitive_queries = [
            "SELECT * FROM users",
            "SELECT id, username, password_hash FROM users WHERE id = 1",
            "SELECT * FROM device_credentials",
            "SELECT * FROM workspace_memberships",
            "SELECT * FROM audit_logs",
            "SELECT * FROM mysql.user",
            "SELECT * FROM information_schema.tables",
        ]
        for query in sensitive_queries:
            resp = client.post("/api/console/sql", json={"query": query})
            assert resp.status_code == 403, f"Query '{query}' should be forbidden but returned {resp.status_code}"
            assert "forbidden" in resp.json().get("detail", "").lower()
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_sql_console_blocks_dos_functions(client):
    """Verify SEC-02 fix: SQL console forbids sleep/benchmark DoS attempts."""
    app.dependency_overrides[require_admin] = override_require_admin
    try:
        dos_queries = [
            "SELECT SLEEP(10)",
            "SELECT sleep (5)",
            "SELECT benchmark(1000000, MD5('test'))",
        ]
        for query in dos_queries:
            resp = client.post("/api/console/sql", json={"query": query})
            assert resp.status_code == 403, f"Query '{query}' should be forbidden"
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_workspace_isolation_in_events(client):
    """Verify SEC-01 fix: Events are isolated by workspace_id."""
    event_service._events.clear()
    event_service._next_id = 1
    app.dependency_overrides[get_event_service] = lambda: event_service

    try:
        # Ingest event for Workspace 10
        resp1 = client.post(
            "/api/events",
            headers={"X-Workspace-ID": "10"},
            json={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pid": 1001,
                "ppid": 1,
                "user": "alice",
                "event_type": "process_created",
                "file_path": "/bin/alice_app",
            },
        )
        assert resp1.status_code == 201

        # Ingest event for Workspace 20
        resp2 = client.post(
            "/api/events",
            headers={"X-Workspace-ID": "20"},
            json={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pid": 2002,
                "ppid": 1,
                "user": "bob",
                "event_type": "process_created",
                "file_path": "/bin/bob_app",
            },
        )
        assert resp2.status_code == 201

        # List events as Workspace 10 -> Should ONLY see Workspace 10 events
        resp_ws10 = client.get("/api/events", headers={"X-Workspace-ID": "10"})
        assert resp_ws10.status_code == 200
        events_ws10 = resp_ws10.json()
        assert len(events_ws10) == 1
        assert events_ws10[0]["pid"] == 1001

        # List events as Workspace 20 -> Should ONLY see Workspace 20 events
        resp_ws20 = client.get("/api/events", headers={"X-Workspace-ID": "20"})
        assert resp_ws20.status_code == 200
        events_ws20 = resp_ws20.json()
        assert len(events_ws20) == 1
        assert events_ws20[0]["pid"] == 2002
    finally:
        app.dependency_overrides.pop(get_event_service, None)


def test_registration_and_login_in_memory_mode(client):
    """Verify that public registration and login work seamlessly in memory mode."""
    # 1. Register a new user
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "username": "krishna_test",
            "email": "krishna_test@example.com",
            "password": "Password123!",
        },
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["username"] == "krishna_test"

    # 2. Login with the newly registered user
    login_resp = client.post(
        "/api/auth/token",
        data={
            "username": "krishna_test",
            "password": "Password123!",
        },
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Access protected /me route
    from app.core.auth import get_current_user
    app.dependency_overrides.pop(get_current_user, None)
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "krishna_test"

