"""User models for authentication."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    uid_linux: int = Field(description="Linux UID for the user")

class UserCreate(UserBase):
    password: str = Field(min_length=6, description="Raw password to be hashed")

class UserInDB(UserBase):
    user_id: int
    password_hash: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserOut(UserBase):
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
