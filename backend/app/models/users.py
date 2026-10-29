"""User models for authentication."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255, description="Email address for the user")
    uid_linux: Optional[int] = Field(default=None, description="Linux UID for the user")
    is_admin: bool = Field(default=False, description="Admin privilege flag")

class UserCreate(UserBase):
    password: str = Field(min_length=6, description="Raw password to be hashed")

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
