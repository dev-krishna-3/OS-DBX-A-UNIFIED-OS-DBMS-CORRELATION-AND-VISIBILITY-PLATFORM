"""Audit Log models."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str = Field(description="Action performed by the user")
    details: Optional[str] = Field(default=None, description="Additional JSON or text details")

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogInDB(AuditLogBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(AuditLogBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
