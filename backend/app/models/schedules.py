"""Models for DBMS schedule serializability analysis."""

from pydantic import BaseModel, Field, PositiveInt, field_validator


class ScheduleOperation(BaseModel):
    transaction_id: PositiveInt
    operation: str = Field(min_length=1, max_length=1)
    data_item: str = Field(min_length=1, max_length=255)

    @field_validator("operation")
    @classmethod
    def operation_is_read_or_write(cls, value: str) -> str:
        value = value.upper()
        if value not in {"R", "W"}:
            raise ValueError("operation must be R or W")
        return value


class ScheduleAnalysisRequest(BaseModel):
    operations: list[ScheduleOperation] = Field(default_factory=list)


class ScheduleAnalysisResult(BaseModel):
    conflict_serializable: bool
    precedence_graph: dict[str, list[int]]
    cycles: list[list[int]] = Field(default_factory=list)
