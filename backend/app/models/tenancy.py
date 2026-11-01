"""Request and response models for workspace and device access."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class WorkspaceOut(BaseModel):
    workspace_id: int
    name: str
    role: Literal["owner", "inspector"]


class InspectorInviteIn(BaseModel):
    username: str = Field(min_length=3, max_length=100)


class InvitationOut(BaseModel):
    invitation_id: str
    workspace_id: int
    workspace_name: str
    invited_by_username: str
    expires_at: datetime


class DeviceCollectionScope(BaseModel):
    process_events: bool = True
    resource_sample_seconds: int = Field(default=0, ge=0, le=3600)
    filesystem_paths: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("filesystem_paths")
    @classmethod
    def validate_paths(cls, paths: list[str]) -> list[str]:
        normalized = []
        for path in paths:
            value = path.strip()
            if not value or value in {".", "..", "/", "\\"}:
                raise ValueError("Choose explicit filesystem paths; root and relative-current paths are not allowed.")
            if "\x00" in value:
                raise ValueError("Filesystem paths cannot contain NUL bytes.")
            normalized.append(value)
        if len({p.casefold() for p in normalized}) != len(normalized):
            raise ValueError("Filesystem paths must be unique.")
        return normalized


class DeviceCreateIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=150)
    operating_system: Literal["windows", "linux", "macos"]
    collection_scope: DeviceCollectionScope
    retention_days: int = Field(ge=1, le=3650)


class DeviceOut(BaseModel):
    device_id: str
    host_id: str
    display_name: str
    operating_system: str
    collection_scope: DeviceCollectionScope
    retention_days: int
    status: str
    last_heartbeat_at: datetime | None = None
    last_event_at: datetime | None = None


class DeviceEnrollmentOut(DeviceOut):
    credential: str
    credential_expires_at: datetime


class DeviceGrantIn(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    can_export: bool = False
