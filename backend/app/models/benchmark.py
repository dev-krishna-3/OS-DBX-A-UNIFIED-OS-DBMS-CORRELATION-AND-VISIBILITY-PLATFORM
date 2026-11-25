"""Models for the DBMS live benchmarking engine."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class BenchmarkScenarioType(str, Enum):
    """Deterministic benchmark scenarios."""
    DBMS_ONLY = "DBMS_ONLY"
    LOCK_CONTENTION = "LOCK_CONTENTION"
    DEADLOCK = "DEADLOCK"
    MIXED = "MIXED"
    STRESS = "STRESS"


class BenchmarkConfig(BaseModel):
    """Configuration for running a deterministic benchmark."""

    model_config = ConfigDict(extra="ignore")

    scenario: BenchmarkScenarioType
    operations: PositiveInt = Field(
        default=100, le=10000, description="Number of database operations to perform"
    )
    concurrency: PositiveInt = Field(
        default=1, le=50, description="Concurrent simulated connections"
    )
    description: str | None = None


class BenchmarkMetrics(BaseModel):
    """Separation of workload metrics and observability overhead."""

    model_config = ConfigDict(extra="forbid")

    # Workload Metrics
    workload_duration_ms: float
    operations_executed: int
    successful_operations: int
    failed_operations: int
    
    # Observability Overhead
    events_captured: int
    dropped_events: int
    correlation_attempts: int
    correlation_successes: int
    avg_correlation_latency_ms: float
    avg_observation_latency_ms: float
    cpu_overhead_percent: float | None = None
    memory_overhead_mb: float | None = None


class BenchmarkResult(BaseModel):
    """Deterministic output of a benchmark run."""

    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    scenario: BenchmarkScenarioType
    config_used: dict[str, Any]
    metrics: BenchmarkMetrics
    started_at: datetime
    ended_at: datetime
    summary: str
