"""Workspace membership and inspector invitations."""

from datetime import datetime, timedelta, timezone
import uuid

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException

from app.config.database import get_connection
from app.core.auth import get_current_user
from app.core.tenancy import WorkspaceAccess, get_current_workspace, require_workspace_owner
from app.models.tenancy import InvitationOut, InspectorInviteIn, WorkspaceOut
from app.models.users import UserInDB

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def db_connection():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.get("", response_model=list[WorkspaceOut])
def list_my_workspaces(
    current_user: UserInDB = Depends(get_current_user),
    connection=Depends(db_connection),
) -> list[WorkspaceOut]:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT w.workspace_id, w.name, wm.role
            FROM workspace_memberships wm
            JOIN workspaces w ON w.workspace_id = wm.workspace_id
            WHERE wm.user_id = %s
            ORDER BY w.workspace_id
            """,
            (current_user.user_id,),
        )
        return [WorkspaceOut(**row) for row in cursor.fetchall()]
    finally:
        cursor.close()


@router.get("/invitations", response_model=list[InvitationOut])
def list_pending_invitations(
    current_user: UserInDB = Depends(get_current_user),
    connection=Depends(db_connection),
) -> list[InvitationOut]:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT i.invitation_id, i.workspace_id, w.name AS workspace_name,
                   inviter.username AS invited_by_username, i.expires_at
            FROM workspace_invitations i
            JOIN workspaces w ON w.workspace_id = i.workspace_id
            JOIN users inviter ON inviter.user_id = i.invited_by
            WHERE i.invited_user_id = %s AND i.accepted_at IS NULL AND i.revoked_at IS NULL
              AND i.expires_at > UTC_TIMESTAMP(6)
            ORDER BY i.created_at DESC
            """,
            (current_user.user_id,),
        )
        return [InvitationOut(**row) for row in cursor.fetchall()]
    finally:
        cursor.close()


@router.post("/{workspace_id}/invitations", response_model=InvitationOut, status_code=201)
def invite_inspector(
    workspace_id: int,
    invite: InspectorInviteIn,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    current_user: UserInDB = Depends(get_current_user),
    connection=Depends(db_connection),
) -> InvitationOut:
    if workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=403, detail="Workspace access denied.")
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, is_admin FROM users WHERE username = %s", (invite.username,))
        invited = cursor.fetchone()
        if not invited:
            raise HTTPException(status_code=404, detail="Inspector account not found.")
        if int(invited["user_id"]) == current_user.user_id:
            raise HTTPException(status_code=400, detail="You already own this workspace.")
        cursor.execute(
            "SELECT 1 FROM workspace_memberships WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, invited["user_id"]),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="This user is already a workspace member.")
        cursor.execute(
            """
            SELECT 1 FROM workspace_invitations
            WHERE workspace_id = %s AND invited_user_id = %s
              AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at > UTC_TIMESTAMP(6)
            """,
            (workspace_id, invited["user_id"]),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="A pending invitation already exists.")
        invitation_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
        cursor.execute(
            """
            INSERT INTO workspace_invitations
                (invitation_id, workspace_id, invited_user_id, invited_by, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (invitation_id, workspace_id, invited["user_id"], current_user.user_id, expires_at),
        )
        cursor.execute("SELECT name FROM workspaces WHERE workspace_id = %s", (workspace_id,))
        workspace_row = cursor.fetchone()
        connection.commit()
        return InvitationOut(
            invitation_id=invitation_id,
            workspace_id=workspace_id,
            workspace_name=workspace_row["name"],
            invited_by_username=current_user.username,
            expires_at=expires_at.replace(tzinfo=timezone.utc),
        )
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not create inspector invitation.") from error
    finally:
        cursor.close()


@router.post("/invitations/{invitation_id}/accept", response_model=WorkspaceOut)
def accept_invitation(
    invitation_id: str,
    current_user: UserInDB = Depends(get_current_user),
    connection=Depends(db_connection),
) -> WorkspaceOut:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT i.workspace_id, w.name
            FROM workspace_invitations i
            JOIN workspaces w ON w.workspace_id = i.workspace_id
            WHERE i.invitation_id = %s AND i.invited_user_id = %s
              AND i.accepted_at IS NULL AND i.revoked_at IS NULL
              AND i.expires_at > UTC_TIMESTAMP(6)
            FOR UPDATE
            """,
            (invitation_id, current_user.user_id),
        )
        invitation = cursor.fetchone()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation is unavailable or expired.")
        cursor.execute(
            """
            INSERT INTO workspace_memberships (workspace_id, user_id, role, invited_by)
            SELECT workspace_id, invited_user_id, 'inspector', invited_by
            FROM workspace_invitations WHERE invitation_id = %s
            """,
            (invitation_id,),
        )
        cursor.execute(
            "UPDATE workspace_invitations SET accepted_at = UTC_TIMESTAMP(6) WHERE invitation_id = %s",
            (invitation_id,),
        )
        connection.commit()
        return WorkspaceOut(
            workspace_id=int(invitation["workspace_id"]),
            name=invitation["name"],
            role="inspector",
        )
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not accept invitation.") from error
    finally:
        cursor.close()


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
def revoke_inspector(
    workspace_id: int,
    user_id: int,
    workspace: WorkspaceAccess = Depends(require_workspace_owner),
    connection=Depends(db_connection),
) -> None:
    if workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=403, detail="Workspace access denied.")
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM workspace_memberships WHERE workspace_id = %s AND user_id = %s AND role = 'inspector'",
            (workspace_id, user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Inspector membership not found.")
        cursor.execute(
            "UPDATE device_access_grants SET revoked_at = UTC_TIMESTAMP(6) WHERE workspace_id = %s AND user_id = %s AND revoked_at IS NULL",
            (workspace_id, user_id),
        )
        cursor.execute(
            "UPDATE workspace_invitations SET revoked_at = UTC_TIMESTAMP(6) WHERE workspace_id = %s AND invited_user_id = %s AND accepted_at IS NULL AND revoked_at IS NULL",
            (workspace_id, user_id),
        )
        connection.commit()
    except mysql.connector.Error as error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Could not revoke inspector access.") from error
    finally:
        cursor.close()
