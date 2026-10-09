"""Deterministic incident fingerprint model."""

from pydantic import BaseModel, ConfigDict, Field


class IncidentFingerprint(BaseModel):
    """Deterministic structural representation of an incident."""
    
    model_config = ConfigDict(extra="forbid")
    
    incident_type: str = Field(..., description="E.g., DEADLOCK")
    transaction_count: int
    lock_count: int
    normalized_structure: str = Field(..., description="Canonical string representing the structure of the incident")
    deterministic_hash: str = Field(..., description="SHA-256 hash of the normalized structure")
