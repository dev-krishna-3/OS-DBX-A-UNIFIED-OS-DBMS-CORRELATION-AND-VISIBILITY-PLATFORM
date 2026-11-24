"""Unit tests for user avatar / profile picture update."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user

client = TestClient(app)


def test_avatar_update_lifecycle():
    # Remove autouse mock for real token auth
    app.dependency_overrides.pop(get_current_user, None)

    # 1. Sign in as admin
    auth_resp = client.post("/api/auth/token", data={"username": "admin", "password": "DevAdminPassword123!"})
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get me - avatar_url should be None or existing
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert "avatar_url" in me_resp.json()

    # 3. Update avatar with cartoon SVG data URL
    test_avatar = "data:image/svg+xml;utf8,<svg><circle cx='50' cy='50' r='50' fill='blue'/></svg>"
    update_resp = client.post("/api/auth/avatar", headers=headers, json={"avatar_url": test_avatar})
    assert update_resp.status_code == 200
    assert update_resp.json()["avatar_url"] == test_avatar

    # 4. Confirm it persists on GET /me
    me_after = client.get("/api/auth/me", headers=headers)
    assert me_after.status_code == 200
    assert me_after.json()["avatar_url"] == test_avatar

    # 5. Clear / Reset avatar to None
    clear_resp = client.post("/api/auth/avatar", headers=headers, json={"avatar_url": None})
    assert clear_resp.status_code == 200
    assert clear_resp.json()["avatar_url"] is None

    # 6. Verify cleared on GET /me
    me_final = client.get("/api/auth/me", headers=headers)
    assert me_final.status_code == 200
    assert me_final.json()["avatar_url"] is None
