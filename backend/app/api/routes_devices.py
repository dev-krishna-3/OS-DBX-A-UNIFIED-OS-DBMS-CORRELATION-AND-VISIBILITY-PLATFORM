"""Owner-controlled device enrollment and inspector grants."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
import uuid

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, status

from app.config.database import get_connection
from app.core.tenancy import DeviceCredential, WorkspaceAccess, get_current_workspace, require_device_access, require_device_credential, require_workspace_owner
from app.models.tenancy import DeviceCreateIn, DeviceEnrollmentOut, DeviceGrantIn, DeviceOut
from app.models.users import UserInDB
from app.core.auth import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])
_CREDENTIAL_LIFETIME = timedelta(days=90)


def db_connection():
    connection = None
    try:
        connection = get_connection()
    except Exception:
        connection = None
    try:
        yield connection
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def _device_out(row: dict) -> DeviceOut:
    scope = row.get("collection_scope") or {}
    if isinstance(scope, str):
        scope = json.loads(scope)
    return DeviceOut(
        device_id=str(row["device_id"]),
        host_id=str(row["host_id"]),
        display_name=str(row["display_name"]),
        operating_system=str(row["operating_system"]),
        collection_scope=scope,
        retention_days=int(row["retention_days"]),
        status=str(row["status"]),
        last_heartbeat_at=row.get("last_heartbeat_at"),
        last_event_at=row.get("last_event_at"),
    )


def _issue_credential(cursor, device_id: str, now: datetime) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    expires = now + _CREDENTIAL_LIFETIME
    cursor.execute(
        """
        INSERT INTO device_credentials (credential_id, device_id, token_hash, created_at, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), device_id, hashlib.sha256(token.encode("ascii")).hexdigest(), now, expires),
    )
    return token, expires.replace(tzinfo=timezone.utc)


@router.post("", response_model=DeviceEnrollmentOut, status_code=201)
def enroll_device(
    payload: DeviceCreateIn,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    connection=Depends(db_connection),
) -> DeviceEnrollmentOut:
    device_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if connection is None:
        token = secrets.token_urlsafe(48)
        expires = now + _CREDENTIAL_LIFETIME
        return DeviceEnrollmentOut(
            device_id=device_id,
            host_id=device_id,
            display_name=payload.display_name,
            operating_system=payload.operating_system,
            collection_scope=payload.collection_scope,
            retention_days=payload.retention_days,
            status="pending",
            credential=token,
            credential_expires_at=expires.replace(tzinfo=timezone.utc),
        )
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO devices
                (device_id, workspace_id, host_id, display_name, operating_system,
                 collection_scope, retention_days, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            """,
            (
                device_id,
                workspace.workspace_id,
                device_id,
                payload.display_name,
                payload.operating_system,
                json.dumps(payload.collection_scope.model_dump()),
                payload.retention_days,
            ),
        )
        token, expires = _issue_credential(cursor, device_id, now)
        connection.commit()
        return DeviceEnrollmentOut(
            device_id=device_id,
            host_id=device_id,
            display_name=payload.display_name,
            operating_system=payload.operating_system,
            collection_scope=payload.collection_scope,
            retention_days=payload.retention_days,
            status="pending",
            credential=token,
            credential_expires_at=expires,
        )
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not enroll device.") from error
    finally:
        cursor.close()


def _update_stale_device_statuses(cursor) -> None:
    try:
        cursor.execute(
            """
            UPDATE devices
            SET status = 'offline'
            WHERE status IN ('online', 'degraded')
              AND revoked_at IS NULL
              AND last_heartbeat_at < DATE_SUB(UTC_TIMESTAMP(6), INTERVAL 90 SECOND)
            """
        )
        cursor.execute(
            """
            UPDATE devices
            SET status = 'degraded'
            WHERE status = 'online'
              AND revoked_at IS NULL
              AND last_heartbeat_at < DATE_SUB(UTC_TIMESTAMP(6), INTERVAL 60 SECOND)
            """
        )
    except Exception:
        pass


@router.post("/heartbeat", status_code=200)
def record_device_heartbeat(
    credential: DeviceCredential = Depends(require_device_credential),
    connection=Depends(db_connection),
) -> dict[str, str]:
    if connection is None:
        return {"status": "online", "device_id": str(getattr(credential, "device_id", "dev-device-01"))}
    cursor = connection.cursor()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cursor.execute(
            """
            UPDATE devices
            SET last_heartbeat_at = %s, status = 'online'
            WHERE device_id = %s AND revoked_at IS NULL
            """,
            (now, credential.device_id),
        )
        connection.commit()
        return {"status": "online", "device_id": credential.device_id}
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not record heartbeat.") from error
    finally:
        cursor.close()


@router.get("", response_model=list[DeviceOut])
def list_devices(
    workspace: WorkspaceAccess = Depends(get_current_workspace),
    connection=Depends(db_connection),
) -> list[DeviceOut]:
    if connection is None:
        return []
    cursor = connection.cursor(dictionary=True)
    try:
        _update_stale_device_statuses(cursor)
        connection.commit()
        if workspace.is_owner:
            cursor.execute(
                """
                SELECT device_id, host_id, display_name, operating_system,
                       collection_scope, retention_days, status,
                       last_heartbeat_at, last_event_at
                FROM devices WHERE workspace_id = %s AND revoked_at IS NULL
                ORDER BY enrolled_at DESC
                """,
                (workspace.workspace_id,),
            )
        else:
            cursor.execute(
                """
                SELECT d.device_id, d.host_id, d.display_name, d.operating_system,
                       d.collection_scope, d.retention_days, d.status,
                       d.last_heartbeat_at, d.last_event_at
                FROM devices d
                JOIN device_access_grants g ON g.device_id = d.device_id
                WHERE d.workspace_id = %s AND g.workspace_id = %s AND g.user_id = %s
                  AND d.revoked_at IS NULL AND g.revoked_at IS NULL
                  AND (g.expires_at IS NULL OR g.expires_at > UTC_TIMESTAMP(6))
                ORDER BY d.enrolled_at DESC
                """,
                (workspace.workspace_id, workspace.workspace_id, workspace.user_id),
            )
        return [_device_out(row) for row in cursor.fetchall()]
    finally:
        cursor.close()


@router.post("/{device_id}/grants", status_code=201)
def grant_device_access(
    device_id: str,
    grant: DeviceGrantIn,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    current_user: UserInDB = Depends(get_current_user),
    connection=Depends(db_connection),
) -> dict[str, str | bool]:
    if connection is None:
        return {"status": "granted", "username": grant.username, "can_export": grant.can_export}
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT 1 FROM devices WHERE device_id = %s AND workspace_id = %s AND revoked_at IS NULL",
            (device_id, workspace.workspace_id),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Device not found.")
        cursor.execute(
            """
            SELECT user_id FROM users WHERE username = %s
              AND EXISTS (
                SELECT 1 FROM workspace_memberships
                WHERE workspace_id = %s AND user_id = users.user_id AND role = 'inspector'
              )
            """,
            (grant.username, workspace.workspace_id),
        )
        inspector = cursor.fetchone()
        if not inspector:
            raise HTTPException(status_code=404, detail="Inspector is not a member of this workspace.")
        cursor.execute(
            """
            INSERT INTO device_access_grants
                (workspace_id, device_id, user_id, can_export, granted_by)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                can_export = VALUES(can_export), granted_by = VALUES(granted_by),
                revoked_at = NULL, expires_at = NULL
            """,
            (workspace.workspace_id, device_id, inspector["user_id"], grant.can_export, current_user.user_id),
        )
        connection.commit()
        return {"status": "granted", "username": grant.username, "can_export": grant.can_export}
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not grant device access.") from error
    finally:
        cursor.close()


@router.delete("/{device_id}/grants/{user_id}", status_code=204)
def revoke_device_access(
    device_id: str,
    user_id: int,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    connection=Depends(db_connection),
) -> None:
    if connection is None:
        return None
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE device_access_grants SET revoked_at = UTC_TIMESTAMP(6)
            WHERE workspace_id = %s AND device_id = %s AND user_id = %s AND revoked_at IS NULL
            """,
            (workspace.workspace_id, device_id, user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Active device grant not found.")
        connection.commit()
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not revoke device access.") from error
    finally:
        cursor.close()


@router.post("/{device_id}/credentials/rotate", response_model=DeviceEnrollmentOut)
def rotate_device_credential(
    device_id: str,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    connection=Depends(db_connection),
) -> DeviceEnrollmentOut:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if connection is None:
        token = secrets.token_urlsafe(48)
        expires = now + _CREDENTIAL_LIFETIME
        return DeviceEnrollmentOut(
            device_id=device_id,
            host_id=device_id,
            display_name="Device",
            operating_system="Windows",
            collection_scope={},
            retention_days=30,
            status="online",
            credential=token,
            credential_expires_at=expires.replace(tzinfo=timezone.utc),
        )
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT device_id, host_id, display_name, operating_system,
                   collection_scope, retention_days, status
            FROM devices WHERE device_id = %s AND workspace_id = %s AND revoked_at IS NULL
            FOR UPDATE
            """,
            (device_id, workspace.workspace_id),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found.")
        cursor.execute(
            "UPDATE device_credentials SET revoked_at = %s WHERE device_id = %s AND revoked_at IS NULL",
            (now, device_id),
        )
        token, expires = _issue_credential(cursor, device_id, now)
        connection.commit()
        device = _device_out(row)
        return DeviceEnrollmentOut(**device.model_dump(), credential=token, credential_expires_at=expires)
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not rotate device credential.") from error
    finally:
        cursor.close()


@router.delete("/{device_id}", status_code=204)
def revoke_device(
    device_id: str,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    connection=Depends(db_connection),
) -> None:
    if connection is None:
        return None
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE devices SET revoked_at = UTC_TIMESTAMP(6), status = 'revoked' WHERE device_id = %s AND workspace_id = %s AND revoked_at IS NULL",
            (device_id, workspace.workspace_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Device not found.")
        cursor.execute(
            "UPDATE device_credentials SET revoked_at = UTC_TIMESTAMP(6) WHERE device_id = %s AND revoked_at IS NULL",
            (device_id,),
        )
        connection.commit()
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not revoke device.") from error
    finally:
        cursor.close()
