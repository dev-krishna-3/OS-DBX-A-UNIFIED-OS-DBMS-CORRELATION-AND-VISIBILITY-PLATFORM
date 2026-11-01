"""Workspace membership and device-grant authorization."""

from dataclasses import dataclass
import hashlib

from fastapi import Depends, Header, HTTPException, status

from app.config.database import get_connection
from app.core.auth import get_current_user
from app.models.users import UserInDB
from app.core.auth import oauth2_optional_scheme


@dataclass(frozen=True)
class DeviceCredential:
    device_id: str
    workspace_id: int


@dataclass(frozen=True)
class WorkspaceAccess:
    workspace_id: int
    user_id: int
    role: str
    device_ids: frozenset[str] | None
    can_export_device_ids: frozenset[str]

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    def can_access_device(self, device_id: str) -> bool:
        return self.is_owner or device_id in (self.device_ids or ())

    def can_export_device(self, device_id: str) -> bool:
        return self.is_owner or device_id in self.can_export_device_ids


async def get_current_workspace(
    current_user: UserInDB = Depends(get_current_user),
    x_workspace_id: int | None = Header(default=None, alias="X-Workspace-ID"),
) -> WorkspaceAccess:
    """Resolve the active workspace only from a current membership."""
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT wm.workspace_id, wm.role
                FROM workspace_memberships wm
                JOIN workspaces w ON w.workspace_id = wm.workspace_id
                WHERE wm.user_id = %s
                ORDER BY wm.workspace_id
                """,
                (current_user.user_id,),
            )
            memberships = cursor.fetchall()
            if x_workspace_id is None:
                if len(memberships) != 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Select a workspace with X-Workspace-ID.",
                    )
                membership = memberships[0]
            else:
                membership = next(
                    (row for row in memberships if int(row["workspace_id"]) == x_workspace_id),
                    None,
                )
                if membership is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied.")

            selected_id = int(membership["workspace_id"])
            role = str(membership["role"])
            if role == "owner":
                return WorkspaceAccess(selected_id, current_user.user_id, role, None, frozenset())

            cursor.execute(
                """
                SELECT device_id, can_export
                FROM device_access_grants
                WHERE workspace_id = %s AND user_id = %s AND revoked_at IS NULL
                  AND (expires_at IS NULL OR expires_at > UTC_TIMESTAMP(6))
                """,
                (selected_id, current_user.user_id),
            )
            grants = cursor.fetchall()
            device_ids = frozenset(str(row["device_id"]) for row in grants)
            export_ids = frozenset(str(row["device_id"]) for row in grants if row["can_export"])
            return WorkspaceAccess(selected_id, current_user.user_id, role, device_ids, export_ids)
        finally:
            cursor.close()
    finally:
        connection.close()


async def require_workspace_owner(
    workspace: WorkspaceAccess = Depends(get_current_workspace),
) -> WorkspaceAccess:
    if not workspace.is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace owner access required.")
    return workspace


def require_device_access(workspace: WorkspaceAccess, device_id: str) -> None:
    if not workspace.can_access_device(device_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device access denied.")


def require_device_export(workspace: WorkspaceAccess, device_id: str) -> None:
    if not workspace.can_export_device(device_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Export permission required.")


async def require_device_credential(
    token: str | None = Depends(oauth2_optional_scheme),
) -> DeviceCredential:
    """Authenticate an active, unexpired per-device bearer credential."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device credential required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT d.device_id, d.workspace_id
                FROM device_credentials c
                JOIN devices d ON d.device_id = c.device_id
                WHERE c.token_hash = %s AND c.revoked_at IS NULL
                  AND (c.expires_at IS NULL OR c.expires_at > UTC_TIMESTAMP(6))
                  AND d.revoked_at IS NULL
                LIMIT 1
                """,
                (token_hash,),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Device credential is invalid, expired, or revoked.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return DeviceCredential(str(row["device_id"]), int(row["workspace_id"]))
        finally:
            cursor.close()
    finally:
        connection.close()
