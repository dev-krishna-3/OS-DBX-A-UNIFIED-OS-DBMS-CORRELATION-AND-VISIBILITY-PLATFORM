"""Formal model for the DBMS-side identity context."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class DBMSIdentityContext(BaseModel):
    """
    Represents the identity chain from the application's OS process down to the
    DBMS query and locks. This model establishes the shared contract with the
    OS collector side without inventing unproven relationships.
    """

    model_config = ConfigDict(extra="forbid")

    os_pid: PositiveInt | None = Field(
        default=None, description="OS process ID from the application"
    )
    connection_id: PositiveInt | None = Field(
        default=None, description="MySQL CONNECTION_ID / PROCESSLIST_ID"
    )
    thread_id: PositiveInt | None = Field(
        default=None, description="MySQL THREAD_ID"
    )
    transaction_id: PositiveInt | None = Field(
        default=None, description="Application transaction ID"
    )
    query_id: PositiveInt | None = Field(
        default=None, description="Backend-assigned query ID"
    )
    lock_ids: list[PositiveInt] = Field(
        default_factory=list, description="Associated lock IDs"
    )

    mapping_state: Literal["MAPPED", "PARTIAL", "UNMAPPED"] = Field(
        default="UNMAPPED", description="State of the identity bridge mapping"
    )

    @property
    def is_fully_mapped(self) -> bool:
        """Return True if the essential OS-to-DBMS link is established."""
        return (
            self.os_pid is not None
            and (self.connection_id is not None or self.thread_id is not None)
            and self.transaction_id is not None
        )
