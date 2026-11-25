"""Audit Log models."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str = Field(description="Action performed by the user")
    details: Optional[str] = Field(default=None, description="Additional JSON or text details")

class AuditLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=255)
    details: Optional[str] = Field(default=None, max_length=10000)

class AuditLogInDB(AuditLogBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(AuditLogBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
