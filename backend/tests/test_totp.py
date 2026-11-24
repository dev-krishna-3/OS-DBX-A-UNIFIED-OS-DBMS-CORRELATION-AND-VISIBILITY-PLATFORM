"""Unit tests for Two-Step Verification (Google Authenticator / TOTP)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user, UserInDB
from app.api.routes_auth import _generate_totp_secret, _verify_totp_code

client = TestClient(app)


def test_totp_algorithm():
    """Verify standard RFC 6238 TOTP generation and verification."""
    secret = _generate_totp_secret()
    assert len(secret) >= 16

    # Test pure Python generation
    import base64, hmac, hashlib, struct, time
    pad = len(secret) % 8
    padded = secret + ("=" * (8 - pad) if pad else "")
    key = base64.b32decode(padded.upper())
    now_counter = int(time.time()) // 30
    counter_bytes = struct.pack(">Q", now_counter)
    h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    h_offset = h[-1] & 0x0F
    valid_code = f"{(struct.unpack('>I', h[h_offset:h_offset + 4])[0] & 0x7FFFFFFF) % 1000000:06d}"

    assert _verify_totp_code(secret, valid_code) is True
    assert _verify_totp_code(secret, "000000") is False


def test_totp_endpoints_lifecycle():
    """Verify setup, invalid code rejection, valid code activation, and disabling."""
    # Pop the autouse mock so real token authentication is tested
    app.dependency_overrides.pop(get_current_user, None)
    # Obtain admin token
    auth_resp = client.post("/api/auth/token", data={"username": "admin", "password": "DevAdminPassword123!"})
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check initial status
    status_resp = client.get("/api/auth/totp/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["totp_enabled"] is False

    # 2. Setup TOTP
    setup_resp = client.post("/api/auth/totp/setup", headers=headers)
    assert setup_resp.status_code == 200
    data = setup_resp.json()
    assert "secret" in data
    assert "qr_code_url" in data
    assert "otpauth://totp/" in data["provisioning_uri"]
    secret = data["secret"]

    # 3. Enable with bad code -> 400
    bad_resp = client.post("/api/auth/totp/enable", headers=headers, json={"code": "000000"})
    assert bad_resp.status_code == 400

    # 4. Generate valid code and enable
    import base64, hmac, hashlib, struct, time
    pad = len(secret) % 8
    padded = secret + ("=" * (8 - pad) if pad else "")
    key = base64.b32decode(padded.upper())
    now_counter = int(time.time()) // 30
    counter_bytes = struct.pack(">Q", now_counter)
    h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    h_offset = h[-1] & 0x0F
    valid_code = f"{(struct.unpack('>I', h[h_offset:h_offset + 4])[0] & 0x7FFFFFFF) % 1000000:06d}"

    enable_resp = client.post("/api/auth/totp/enable", headers=headers, json={"code": valid_code})
    assert enable_resp.status_code == 200
    assert enable_resp.json()["totp_enabled"] is True

    # 5. Status is now enabled
    status_after = client.get("/api/auth/totp/status", headers=headers)
    assert status_after.json()["totp_enabled"] is True

    # 6. Test Login Challenge Flow when TOTP is enabled
    # 6a. Normal login now triggers 2FA challenge
    login_resp = client.post("/api/auth/token", data={"username": "admin", "password": "DevAdminPassword123!"})
    assert login_resp.status_code == 200
    challenge_data = login_resp.json()
    assert challenge_data.get("requires_totp") is True
    assert challenge_data.get("challenge_token") is not None
    challenge_token = challenge_data["challenge_token"]

    # 6b. Verify with invalid code -> 400
    bad_verify = client.post("/api/auth/totp/verify-login", json={"challenge_token": challenge_token, "code": "000000"})
    assert bad_verify.status_code == 400

    # 6c. Verify with valid code -> 200 and access_token issued
    now_counter = int(time.time()) // 30
    counter_bytes = struct.pack(">Q", now_counter)
    h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    h_offset = h[-1] & 0x0F
    challenge_code = f"{(struct.unpack('>I', h[h_offset:h_offset + 4])[0] & 0x7FFFFFFF) % 1000000:06d}"

    good_verify = client.post("/api/auth/totp/verify-login", json={"challenge_token": challenge_token, "code": challenge_code})
    assert good_verify.status_code == 200
    new_token_data = good_verify.json()
    assert new_token_data["access_token"]
    assert new_token_data["token_type"] == "bearer"

    # 6d. Check that access token works on authenticated endpoint
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token_data['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"

    # 7. Disable TOTP
    disable_resp = client.post("/api/auth/totp/disable", headers=headers)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["totp_enabled"] is False

    # 8. Final status
    status_final = client.get("/api/auth/totp/status", headers=headers)
    assert status_final.json()["totp_enabled"] is False

    # 9. Verify login returns direct access token again (no 2FA challenge)
    direct_login = client.post("/api/auth/token", data={"username": "admin", "password": "DevAdminPassword123!"})
    assert direct_login.status_code == 200
    assert direct_login.json().get("requires_totp") is False
    assert direct_login.json().get("access_token") != ""
