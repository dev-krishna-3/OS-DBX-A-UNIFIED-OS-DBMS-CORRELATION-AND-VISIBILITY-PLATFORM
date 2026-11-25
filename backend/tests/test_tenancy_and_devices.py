"""Unit and authorization tests for Multi-Tenancy, Workspaces, and Device Access Control."""

from datetime import datetime, timezone
import hashlib
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.models.users import UserInDB
from app.core.auth import get_current_user
from app.core.tenancy import (
    DeviceCredential,
    WorkspaceAccess,
    require_device_credential,
    require_workspace_owner,
    require_device_access,
    require_device_export,
)
from app.api.routes_devices import db_connection as device_db_connection
from app.api.routes_workspaces import db_connection as workspace_db_connection

client = TestClient(app)


def test_workspace_access_owner_model():
    """An owner should have full access to all devices and exports."""
    access = WorkspaceAccess(
        workspace_id=1,
        user_id=10,
        role="owner",
        device_ids=None,
        can_export_device_ids=frozenset(),
    )
    assert access.is_owner is True
    assert access.can_access_device("any-device-uuid") is True
    assert access.can_export_device("any-device-uuid") is True


def test_workspace_access_inspector_model():
    """An inspector should only access granted devices, and only export with explicit grant."""
    allowed_device = "dev-1111-2222-3333"
    exportable_device = "dev-4444-5555-6666"
    forbidden_device = "dev-9999-9999-9999"

    access = WorkspaceAccess(
        workspace_id=2,
        user_id=20,
        role="inspector",
        device_ids=frozenset([allowed_device, exportable_device]),
        can_export_device_ids=frozenset([exportable_device]),
    )
    assert access.is_owner is False
    assert access.can_access_device(allowed_device) is True
    assert access.can_access_device(exportable_device) is True
    assert access.can_access_device(forbidden_device) is False

    # Export checks
    assert access.can_export_device(allowed_device) is False
    assert access.can_export_device(exportable_device) is True
    assert access.can_export_device(forbidden_device) is False


def test_require_device_access_guards():
    """require_device_access and require_device_export should raise 403 on violations."""
    access = WorkspaceAccess(
        workspace_id=2,
        user_id=20,
        role="inspector",
        device_ids=frozenset(["dev-allowed"]),
        can_export_device_ids=frozenset(),
    )
    # Allowed device does not raise
    require_device_access(access, "dev-allowed")

    # Forbidden device raises 403
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        require_device_access(access, "dev-forbidden")
    assert exc.value.status_code == 403

    # Export without grant raises 403
    with pytest.raises(HTTPException) as exc:
        require_device_export(access, "dev-allowed")
    assert exc.value.status_code == 403


def test_device_heartbeat_updates_lease():
    """POST /api/devices/heartbeat should update device status and lease timestamp."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    app.dependency_overrides[device_db_connection] = lambda: mock_conn
    app.dependency_overrides[require_device_credential] = lambda: DeviceCredential(
        device_id="test-dev-uuid", workspace_id=1
    )
    try:
        resp = client.post("/api/devices/heartbeat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["device_id"] == "test-dev-uuid"
        assert mock_cursor.execute.called
        assert mock_conn.commit.called
    finally:
        app.dependency_overrides.pop(device_db_connection, None)
        app.dependency_overrides.pop(require_device_credential, None)


def test_device_enrollment_owner_only():
    """POST /api/devices should generate token and save device under owner workspace."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    owner_access = WorkspaceAccess(
        workspace_id=5,
        user_id=1,
        role="owner",
        device_ids=None,
        can_export_device_ids=frozenset(),
    )
    app.dependency_overrides[device_db_connection] = lambda: mock_conn
    app.dependency_overrides[require_workspace_owner] = lambda: owner_access

    payload = {
        "display_name": "Forensic Workstation 1",
        "operating_system": "windows",
        "collection_scope": {"processes": True, "filesystem": True},
        "retention_days": 30,
    }
    try:
        resp = client.post("/api/devices", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Forensic Workstation 1"
        assert data["status"] == "pending"
        assert len(data["credential"]) > 20
        assert mock_conn.commit.called
    finally:
        app.dependency_overrides.pop(device_db_connection, None)
        app.dependency_overrides.pop(require_workspace_owner, None)


def test_unauthenticated_device_credential_rejected():
    """Ingesting OS events without a valid device credential must be rejected with 401."""
    # Ensure no device credential override is active
    app.dependency_overrides.pop(require_device_credential, None)

    payload = {
        "event_id": str(uuid.uuid4()),
        "source": "OS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "file_modified",
        "host_id": "unknown-host",
        "file_path": "C:\\temp\\unauthorized.txt",
        "pid": None,
    }
    resp = client.post("/api/os-events/filesystem", json=payload)
    assert resp.status_code == 401
    assert "Device credential required" in resp.json().get("detail", "")
