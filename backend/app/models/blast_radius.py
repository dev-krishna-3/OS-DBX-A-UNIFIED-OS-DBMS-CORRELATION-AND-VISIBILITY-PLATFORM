"""Models for the deterministic blast-radius analyzer."""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class ImpactLevel(str, Enum):
    """Levels of deterministic impact."""
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    POTENTIAL = "POTENTIAL"


class ResourceType(str, Enum):
    """Types of resources that can be affected."""
    TRANSACTION = "TRANSACTION"
    QUERY = "QUERY"
    LOCK = "LOCK"
    PROCESS = "PROCESS"


class ImpactEvidence(BaseModel):
    """Deterministic reason for the impact."""
    
    model_config = ConfigDict(extra="forbid")
    
    rule_applied: str = Field(..., description="The deterministic rule that determined this impact.")
    relationship: str = Field(..., description="The relationship (e.g. 'shares lock with Tx 4').")


class AffectedResource(BaseModel):
    """A resource affected by an incident."""
    
    model_config = ConfigDict(extra="forbid")
    
    resource_type: ResourceType
    resource_id: str
    impact_level: ImpactLevel
    evidence: ImpactEvidence


class BlastRadiusResult(BaseModel):
    """The result of a blast-radius analysis."""
    
    model_config = ConfigDict(extra="forbid")
    
    incident_id: PositiveInt
    incident_type: str = Field(..., description="E.g., DEADLOCK")
    affected_resources: list[AffectedResource] = Field(default_factory=list)
    
    @property
    def direct_impact_count(self) -> int:
        return sum(1 for r in self.affected_resources if r.impact_level == ImpactLevel.DIRECT)
        
    @property
    def indirect_impact_count(self) -> int:
        return sum(1 for r in self.affected_resources if r.impact_level == ImpactLevel.INDIRECT)
        
    @property
    def potential_impact_count(self) -> int:
        return sum(1 for r in self.affected_resources if r.impact_level == ImpactLevel.POTENTIAL)

    def summary(self) -> str:
        return (f"Blast Radius for Incident {self.incident_id}: "
                f"{self.direct_impact_count} Direct, "
                f"{self.indirect_impact_count} Indirect, "
                f"{self.potential_impact_count} Potential")
