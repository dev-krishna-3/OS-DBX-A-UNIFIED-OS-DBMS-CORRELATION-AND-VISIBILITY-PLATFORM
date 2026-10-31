"""Release-Readiness and Security Hardening Verification Tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user

client = TestClient(app)


def test_security_headers_present():
    """Verify standard security headers are injected into all HTTP responses."""
    resp = client.get("/health")
    assert resp.status_code == 200
    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("Permissions-Policy", "")


def test_auth_rate_limiting():
    """Verify brute-force rate limiter triggers after repeated invalid login attempts."""
    for _ in range(15):
        resp = client.post("/api/auth/token", data={"username": "invalid_attacker_user", "password": "wrongpassword"})
        assert resp.status_code in (401, 429)

    # 16th attempt should be blocked with 429 Too Many Requests
    blocked_resp = client.post("/api/auth/token", data={"username": "invalid_attacker_user", "password": "wrongpassword"})
    assert blocked_resp.status_code == 429
    assert "Too many failed login attempts" in blocked_resp.json().get("detail", "")


def test_authenticated_endpoints_and_aliases():
    """Verify newly mapped routes and aliases work under valid authentication."""
    # Authenticate as admin
    auth_resp = client.post("/api/auth/token", data={"username": "admin", "password": "Admin@OSDBX2026!"})
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Alias GET /api/os-events
    r_os = client.get("/api/os-events", headers=headers)
    assert r_os.status_code == 200
    assert isinstance(r_os.json(), list)

    # 2. Alias GET /api/simulations/scenarios
    r_sim = client.get("/api/simulations/scenarios", headers=headers)
    assert r_sim.status_code == 200
    scenarios = r_sim.json()
    assert len(scenarios) >= 5
    assert any(s["id"] == "cpu_scheduling" for s in scenarios)

    # 3. Alias GET /api/incidents/{id}/blast-radius
    r_blast = client.get("/api/v1/incidents/1/blast-radius", headers=headers)
    assert r_blast.status_code == 200
    assert "affected_resources" in r_blast.json()

    # 4. Alias GET /api/benchmarks/scenarios
    r_bench = client.get("/api/v1/benchmarks/scenarios", headers=headers)
    assert r_bench.status_code == 200
    assert isinstance(r_bench.json(), list)


def test_audit_authorization_rbac():
    """Verify non-admin users cannot read OR write audit logs (403), but admin users can."""
    # 1. Non-admin user (from default conftest override: testuser, uid 1000)
    # Reading audit logs
    r_non_admin_get = client.get("/api/audit/?limit=5")
    assert r_non_admin_get.status_code == 403
    assert "Access Denied" in r_non_admin_get.json()["detail"]

    # Writing audit logs as non-admin
    r_non_admin_post = client.post("/api/audit/", json={"action": "ILLEGAL_MEMBER_ACTION", "details": "trying to audit"})
    assert r_non_admin_post.status_code == 403
    assert "Access Denied" in r_non_admin_post.json()["detail"]

    # 2. Admin user
    app.dependency_overrides[get_current_user] = lambda: {"username": "admin", "uid_linux": 0, "is_admin": True}
    try:
        r_admin_get = client.get("/api/audit/?limit=5")
        assert r_admin_get.status_code == 200
        assert isinstance(r_admin_get.json(), list)

        r_admin_post = client.post("/api/audit/", json={"action": "ADMIN_VERIFIED_CHECK", "details": "authorized admin audit"})
        assert r_admin_post.status_code == 201
        assert r_admin_post.json()["status"] == "success"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
