"""Recovery experiment API."""

from fastapi import APIRouter

from app.models.recovery import RecoveryRequest, RecoveryResult
from app.services.recovery_service import RecoveryService

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post("/recover", response_model=RecoveryResult)
def recover(request: RecoveryRequest) -> RecoveryResult:
    return RecoveryService().recover(request.initial_state, request.logs)
