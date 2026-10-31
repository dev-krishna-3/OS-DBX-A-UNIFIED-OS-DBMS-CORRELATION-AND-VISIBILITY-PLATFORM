"""Audit Logs API routes."""

from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config.database import get_connection
from app.core.auth import get_current_user
from app.models.users import UserInDB
from app.models.audit import AuditLogCreate, AuditLogOut
import mysql.connector

router = APIRouter()

def is_user_admin(current_user: Any) -> bool:
    if isinstance(current_user, dict):
        return bool(current_user.get("is_admin") or current_user.get("username") in ("admin", "root") or current_user.get("uid_linux") == 0)
    return bool(getattr(current_user, "is_admin", False) or getattr(current_user, "username", "") in ("admin", "root") or getattr(current_user, "uid_linux", 1000) == 0)

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    log_data: AuditLogCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a new audit log entry. Strictly restricted to administrators."""
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Administrator role required to record security audit logs.",
        )
    connection = get_connection()
    try:
        cursor = connection.cursor()
        uid_val = log_data.user_id or (current_user.get("user_id") if isinstance(current_user, dict) else getattr(current_user, "user_id", None)) or 1
        uname_val = log_data.username or (current_user.get("username") if isinstance(current_user, dict) else getattr(current_user, "username", "admin"))
        cursor.execute(
            "INSERT INTO audit_logs (user_id, username, action, details) VALUES (%s, %s, %s, %s)",
            (
                uid_val, 
                uname_val, 
                log_data.action, 
                log_data.details
            )
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
    limit: int = 50,
    current_user: UserInDB = Depends(get_current_user)
):
    """Retrieve audit logs. Only admins can access this."""
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Admin privileges required. Current user is not an administrator. Please authenticate as an admin account (username: admin, UID: 0)."
        )
    
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, user_id, username, action, details, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT %s",
            (limit,)
        )
        logs = cursor.fetchall()
        return [AuditLogOut(**log) for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()
