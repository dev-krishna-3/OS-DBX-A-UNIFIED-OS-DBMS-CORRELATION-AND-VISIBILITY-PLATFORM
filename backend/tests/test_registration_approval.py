"""Tests for public registration request and admin approval workflow."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user, require_admin, UserInDB
from app.api.routes_auth import _memory_registration_requests

client = TestClient(app)


def test_admin_dev_login_credentials():
    """Verify admin can log in with both DevAdminPassword123! and admin in dev mode."""
    # Test 1: DevAdminPassword123!
    resp1 = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": "DevAdminPassword123!"},
    )
    assert resp1.status_code == 200, resp1.text
    assert "access_token" in resp1.json()

    # Test 2: admin / admin fallback
    resp2 = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": "admin"},
    )
    assert resp2.status_code == 200, resp2.text
    assert "access_token" in resp2.json()


def test_registration_request_and_admin_approval_lifecycle():
    """Verify the full lifecycle: request -> pending login blocked -> admin approve -> successful login."""
    _memory_registration_requests.clear()
    # Pop the autouse mock so real token authentication is tested
    app.dependency_overrides.pop(get_current_user, None)

    try:
        # 1. Public user submits registration request
        req_payload = {
            "username": "mushkan_test",
            "email": "mushkan012@example.com",
            "password": "SecurePassword123!",
            "requested_role": "inspector",
            "reason": "Observability inspection for university lab testing",
        }
        req_resp = client.post("/api/auth/request-access", json=req_payload)
        assert req_resp.status_code == 201, req_resp.text
        req_data = req_resp.json()
        assert req_data["username"] == "mushkan_test"
        assert req_data["status"] == "PENDING"
        request_id = req_data["request_id"]

        # 2. Duplicate submission with same username should be rejected
        dup_resp = client.post("/api/auth/request-access", json=req_payload)
        assert dup_resp.status_code == 400
        assert "already pending" in dup_resp.json()["detail"].lower()

        # 3. User attempts to log in while request is still PENDING -> Should be blocked with 403
        login_attempt_resp = client.post(
            "/api/auth/token",
            data={"username": "mushkan_test", "password": "SecurePassword123!"},
        )
        assert login_attempt_resp.status_code == 403
        assert "pending administrator approval" in login_attempt_resp.json()["detail"].lower()

        # 4. Admin lists pending registration requests
        # Login as admin to get real admin token
        admin_auth = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "DevAdminPassword123!"},
        )
        assert admin_auth.status_code == 200
        admin_token = admin_auth.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Verify admin can list requests
        list_resp = client.get("/api/auth/admin/requests", headers=admin_headers)
        assert list_resp.status_code == 200, list_resp.text
        requests = list_resp.json()
        assert any(r["request_id"] == request_id for r in requests)

        # 5. Admin approves the request with access level 'inspector'
        approve_resp = client.post(
            f"/api/auth/admin/requests/{request_id}/approve",
            headers=admin_headers,
            json={"approved_role": "inspector"},
        )
        assert approve_resp.status_code == 200, approve_resp.text
        approved_data = approve_resp.json()
        assert approved_data["status"] == "APPROVED"
        assert approved_data["approved_role"] == "inspector"

        # 6. Now approved user logs in with their credentials -> Should succeed!
        login_success_resp = client.post(
            "/api/auth/token",
            data={"username": "mushkan_test", "password": "SecurePassword123!"},
        )
        assert login_success_resp.status_code == 200, login_success_resp.text
        token_data = login_success_resp.json()
        assert "access_token" in token_data
        user_token = token_data["access_token"]

        # 7. Check /me for the newly activated user
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
        assert me_resp.status_code == 200
        user_info = me_resp.json()
        assert user_info["username"] == "mushkan_test"
        assert user_info["email"] == "mushkan012@example.com"
    finally:
        pass
