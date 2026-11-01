"""Audit Logs API routes."""

import threading
from datetime import datetime, timezone
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config.database import get_connection
from app.config.settings import settings
from app.core.auth import get_current_user
from app.models.users import UserInDB
from app.models.audit import AuditLogCreate, AuditLogOut

router = APIRouter()

_memory_audit_logs: list[dict] = []
_audit_lock = threading.Lock()
_next_audit_id = 1


def is_user_admin(current_user: Any) -> bool:
    if isinstance(current_user, dict):
        return bool(current_user.get("is_admin"))
    return bool(getattr(current_user, "is_admin", False))


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    log_data: AuditLogCreate,
    current_user: UserInDB = Depends(get_current_user),
):
    """Create a new audit log entry. Strictly restricted to administrators."""
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Administrator role required to record security audit logs.",
        )
    uid_val = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id
    uname_val = current_user.get("username", "admin") if isinstance(current_user, dict) else current_user.username

    if settings.event_storage.strip().lower() == "memory":
        global _next_audit_id
        with _audit_lock:
            entry = {
                "id": _next_audit_id,
                "user_id": uid_val,
                "username": uname_val,
                "action": log_data.action,
                "details": log_data.details,
                "timestamp": datetime.now(timezone.utc),
            }
            _next_audit_id += 1
            _memory_audit_logs.insert(0, entry)
            if len(_memory_audit_logs) > 1000:
                _memory_audit_logs.pop()
        return {"status": "success", "message": "Audit log recorded"}

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (user_id, username, action, details) VALUES (%s, %s, %s, %s)",
            (
                uid_val,
                uname_val,
                log_data.action,
                log_data.details,
            ),
        )
        connection.commit()
        return {"status": "success", "message": "Audit log recorded"}
    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@router.get("/", response_model=List[AuditLogOut])
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: UserInDB = Depends(get_current_user),
):
    """Retrieve audit logs. Only admins can access this."""
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Admin privileges required. Current user is not an administrator. Please authenticate as an admin account (username: admin, UID: 0).",
        )

    if settings.event_storage.strip().lower() == "memory":
        with _audit_lock:
            return [AuditLogOut(**log) for log in _memory_audit_logs[:limit]]

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, user_id, username, action, details, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT %s",
            (limit,),
        )
        logs = cursor.fetchall()
        return [AuditLogOut(**log) for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()
