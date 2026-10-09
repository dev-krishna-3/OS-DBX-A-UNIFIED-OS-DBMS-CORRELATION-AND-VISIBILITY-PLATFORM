"""API routes for deterministic blast-radius analysis."""

from fastapi import APIRouter, Depends, Path

from app.config.database import get_connection
from app.models.blast_radius import BlastRadiusResult
from app.repositories.lock_repository import LockRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.blast_radius_service import BlastRadiusService
from app.services.deadlock_service import DeadlockService
from app.services.lock_manager import LockManager
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents", "blast-radius"])


def get_blast_radius_service(connection=Depends(get_connection)):
    try:
        lock_manager = LockManager(LockRepository(connection))
        transaction_service = TransactionService(TransactionRepository(connection), lock_manager)
        deadlock_service = DeadlockService()
        yield BlastRadiusService(
            deadlock_service=deadlock_service,
            lock_manager=lock_manager,
            transaction_service=transaction_service
        )
    finally:
        connection.close()


@router.get("/{incident_id}/blast-radius", response_model=BlastRadiusResult)
async def get_blast_radius(
    incident_id: int = Path(..., description="The ID of the incident to analyze"),
    service: BlastRadiusService = Depends(get_blast_radius_service)
) -> BlastRadiusResult:
    """Calculate the deterministic blast radius for a given incident."""
    return service.analyze_deadlock_incident(incident_id)
