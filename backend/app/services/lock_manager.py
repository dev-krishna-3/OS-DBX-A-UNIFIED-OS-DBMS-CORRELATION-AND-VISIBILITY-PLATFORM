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

    def acquire_lock(self, transaction_id: int, data_item: str, lock_type) -> LockRecord:
        from app.models.locks import LockType
        l_type = lock_type if isinstance(lock_type, LockType) else LockType(str(lock_type))
        return self.acquire(
            LockRequest(
                transaction_id=transaction_id,
                data_item=data_item,
                lock_type=l_type,
            )
        )

    def get_all_locks(self):
        from app.models.deadlocks import LockSnapshot
        from app.models.locks import LockStatus, LockType
        if hasattr(self.repository, "active_locks"):
            rows = self.repository.active_locks()
            return [
                LockSnapshot(
                    transaction_id=int(r["transaction_id"]),
                    data_item=str(r["data_item"]),
                    lock_type=LockType(r["lock_type"]),
                    status=LockStatus(r["status"]),
                )
                for r in rows
            ]
        return []

    def release_all(self, transaction_id: int) -> int:
        return self.repository.release_all(transaction_id, utc_now())

