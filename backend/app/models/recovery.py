"""Models for deterministic WAL-style recovery experiments."""

from pydantic import BaseModel, Field, PositiveInt


class RecoveryLogEntry(BaseModel):
    sequence: PositiveInt
    transaction_id: PositiveInt
    log_type: str = Field(min_length=1, max_length=50)
    data_item: str | None = None
    old_value: str | None = None
    new_value: str | None = None


class RecoveryRequest(BaseModel):
    initial_state: dict[str, str] = Field(default_factory=dict)
    logs: list[RecoveryLogEntry] = Field(default_factory=list)


class RecoveryResult(BaseModel):
    final_state: dict[str, str]
    redone_transactions: list[int]
    undone_transactions: list[int]
    committed_transactions: list[int]
