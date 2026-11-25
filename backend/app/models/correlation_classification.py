"""Models for correlation classification and evidence completeness."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class CorrelationClassification(str, Enum):
    """Three-state classification for cross-layer relationships."""
    DIRECT = "DIRECT"
    TEMPORAL = "TEMPORAL"
    NONE = "NONE"


class EvidenceScore(BaseModel):
    """Deterministic representation of evidence completeness.

    Each boolean flag represents one independently verified deterministic
    check.  The ``to_summary()`` string (e.g. '5/8 evidence checks
    satisfied') matches the format that the OS collector emits via
    ``evidence_completeness``.  This is a count, not a probability.
    """

    model_config = ConfigDict(extra="forbid")

    pid_match: bool = False
    db_connection_match: bool = False
    transaction_match: bool = False
    query_match: bool = False
    timestamp_relation: bool = False
    event_ordering: bool = False
    lock_relation: bool = False
    # True when all events in the candidate set share the same host_id.
    host_match: bool = False

    @property
    def total_factors(self) -> int:
        """Total number of deterministic factors evaluated."""
        return 8

    @property
    def factors_met(self) -> int:
        """Number of satisfied deterministic factors."""
        return sum(
            [
                self.pid_match,
                self.db_connection_match,
                self.transaction_match,
                self.query_match,
                self.timestamp_relation,
                self.event_ordering,
                self.lock_relation,
                self.host_match,
            ]
        )

    def to_summary(self) -> str:
        """Return a deterministic string like '5/8 evidence checks satisfied'."""
        return f"{self.factors_met}/{self.total_factors} evidence checks satisfied"
