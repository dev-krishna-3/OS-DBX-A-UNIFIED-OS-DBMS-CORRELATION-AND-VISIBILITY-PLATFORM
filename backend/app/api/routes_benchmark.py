"""API routes for deterministic live benchmarking."""

from fastapi import APIRouter, Depends, Request

from app.config.database import get_connection
from app.models.benchmark import BenchmarkConfig, BenchmarkResult, BenchmarkScenarioType
from app.repositories.lock_repository import LockRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.benchmark_service import BenchmarkRunnerService
from app.services.lock_manager import LockManager
from app.services.transaction_service import TransactionService
from app.core.auth import require_admin
from app.api.routes_auth import check_rate_limit, record_rate_limited_attempt

router = APIRouter(tags=["benchmarks"])


def limit_benchmark_runs(request: Request) -> None:
    key = (f"benchmark:{request.client.host if request.client else 'unknown'}",)
    check_rate_limit(key, max_attempts=3, window_seconds=60)
    record_rate_limited_attempt(key, window_seconds=60)


def get_benchmark_service(connection=Depends(get_connection)):
    try:
        lock_manager = LockManager(LockRepository(connection))
        transaction_service = TransactionService(TransactionRepository(connection), lock_manager)
        yield BenchmarkRunnerService(transaction_service=transaction_service, lock_manager=lock_manager)
    finally:
        connection.close()


@router.get("/api/v1/benchmarks/scenarios", response_model=list[str])
@router.get("/api/benchmark/scenarios", response_model=list[str], include_in_schema=False)
@router.get("/api/benchmarks/scenarios", response_model=list[str], include_in_schema=False)
async def get_scenarios() -> list[str]:
    """List available deterministic benchmark scenarios."""
    return [scenario.value for scenario in BenchmarkScenarioType]


@router.post("/api/v1/benchmarks/run", response_model=BenchmarkResult, dependencies=[Depends(require_admin), Depends(limit_benchmark_runs)])
@router.post("/api/benchmark/run", response_model=BenchmarkResult, include_in_schema=False, dependencies=[Depends(require_admin), Depends(limit_benchmark_runs)])
@router.post("/api/benchmarks/run", response_model=BenchmarkResult, include_in_schema=False, dependencies=[Depends(require_admin), Depends(limit_benchmark_runs)])
async def run_benchmark(config: BenchmarkConfig, service: BenchmarkRunnerService = Depends(get_benchmark_service)) -> BenchmarkResult:
    """Execute a deterministic benchmark scenario and return measurements."""
    return service.run_benchmark(config)

