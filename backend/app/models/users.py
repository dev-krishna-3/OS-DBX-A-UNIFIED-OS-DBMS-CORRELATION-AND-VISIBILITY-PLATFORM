"""User models for authentication."""

from typing import Optional
from datetime import datetime
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255, description="Email address for the user")
    uid_linux: Optional[int] = Field(default=None, description="Linux UID for the user")
    is_admin: bool = Field(default=False, description="Admin privilege flag")

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    password: str = Field(min_length=12, description="Raw password to be hashed")
    model_config = ConfigDict(extra="forbid")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,99}", value):
            raise ValueError("Username must use 3–100 letters, numbers, dots, underscores, or hyphens.")
        return value

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value

class UserInDB(UserBase):
    user_id: int
    uid_linux: int = 1000
    password_hash: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserOut(UserBase):
    user_id: int
    uid_linux: int = 1000
    created_at: datetime
    email_notification_sent: bool = Field(default=False, description="Whether an email notification was sent")
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    email_notification_sent: bool = Field(default=False, description="Whether an email notification was sent")

class TokenData(BaseModel):
    username: Optional[str] = None


class RegistrationRequestCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, description="Raw password to be hashed")
    requested_role: str = Field(default="inspector", description="Requested role: inspector, member, owner")
    reason: Optional[str] = Field(default="", max_length=500, description="Reason for access request")
    model_config = ConfigDict(extra="forbid")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,99}", value):
            raise ValueError("Username must use 3–100 letters, numbers, dots, underscores, or hyphens.")
        return value

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value

    @field_validator("requested_role")
    @classmethod
    def validate_requested_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"inspector", "member", "owner"}:
            return "inspector"
        return normalized


class RegistrationRequestOut(BaseModel):
    request_id: str
    username: str
    email: str
    status: str  # "PENDING", "APPROVED", "REJECTED"
    requested_role: str
    approved_role: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class RegistrationApprovalAction(BaseModel):
    approved_role: str = Field(default="inspector", description="Assigned role: inspector, member, or owner")

    @field_validator("approved_role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"inspector", "member", "owner"}:
            return "inspector"
        return normalized

