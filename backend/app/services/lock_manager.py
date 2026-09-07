"""Lock manager implementing the Strict Two-Phase Locking rules."""

from app.models.locks import LockRecord, LockRequest
from app.repositories.lock_repository import LockRepository
from app.services.transaction_service import utc_now


class LockManager:
    def __init__(self, repository: LockRepository) -> None:
        self.repository = repository

    def acquire(self, request: LockRequest) -> LockRecord:
        result = self.repository.acquire(request, utc_now())
        return LockRecord(**result)

    def release_all(self, transaction_id: int) -> int:
        return self.repository.release_all(transaction_id, utc_now())
