"""Models and constants for the transaction manager."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransactionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


class IsolationLevel(str, Enum):
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


class BeginTransactionRequest(BaseModel):
    pid: int = Field(..., gt=0)
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED


class TransactionOperationRequest(BaseModel):
    data_item: str = Field(..., min_length=1)


class Transaction(BaseModel):
    transaction_id: int
    pid: int
    status: TransactionStatus
    isolation_level: IsolationLevel
    start_time: datetime
    end_time: datetime | None = None


class TransactionOperation(BaseModel):
    operation_id: int
    transaction_id: int
    operation_type: str
    data_item: str | None
    sequence_no: int
    timestamp: datetime
