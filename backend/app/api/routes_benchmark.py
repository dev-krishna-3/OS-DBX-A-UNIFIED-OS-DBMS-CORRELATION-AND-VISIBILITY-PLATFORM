"""API routes for deterministic live benchmarking."""

from fastapi import APIRouter, Depends

from app.config.database import get_connection
from app.models.benchmark import BenchmarkConfig, BenchmarkResult, BenchmarkScenarioType
from app.repositories.lock_repository import LockRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.benchmark_service import BenchmarkRunnerService
from app.services.lock_manager import LockManager
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])


def get_benchmark_service(connection=Depends(get_connection)):
    try:
        lock_manager = LockManager(LockRepository(connection))
        transaction_service = TransactionService(TransactionRepository(connection), lock_manager)
        yield BenchmarkRunnerService(transaction_service=transaction_service, lock_manager=lock_manager)
    finally:
        connection.close()


@router.get("/scenarios", response_model=list[str])
async def get_scenarios() -> list[str]:
    """List available deterministic benchmark scenarios."""
    return [scenario.value for scenario in BenchmarkScenarioType]


@router.post("/run", response_model=BenchmarkResult)
async def run_benchmark(config: BenchmarkConfig, service: BenchmarkRunnerService = Depends(get_benchmark_service)) -> BenchmarkResult:
    """Execute a deterministic benchmark scenario and return measurements."""
    return service.run_benchmark(config)
