"""Audit Logs API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config.database import get_connection
from app.core.auth import get_current_user
from app.models.users import UserInDB
from app.models.audit import AuditLogCreate, AuditLogOut
import mysql.connector

router = APIRouter()

def is_user_admin(current_user: UserInDB) -> bool:
    return current_user.is_admin

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    log_data: AuditLogCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a new audit log entry. Anyone logged in can create logs."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (user_id, username, action, details) VALUES (%s, %s, %s, %s)",
            (
                log_data.user_id or current_user.user_id, 
                log_data.username or current_user.username, 
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    
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
