"""Business rules for the small transaction manager milestone."""

from datetime import datetime, timezone

from app.models.locks import LockRequest, LockType
from app.repositories.transaction_repository import TransactionRepository


def utc_now() -> datetime:
    """Return a naive UTC datetime suitable for MySQL DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TransactionService:
    def __init__(self, repository: TransactionRepository, lock_manager=None) -> None:
        self.repository = repository
        self.lock_manager = lock_manager

    def begin(self, pid: int, isolation_level: str) -> int:
        return self.repository.begin(pid, isolation_level, utc_now())

    def _require_lock_manager(self):
        if self.lock_manager is None:
            raise RuntimeError("TransactionService requires a LockManager for transaction operations")
        return self.lock_manager

    def read(self, transaction_id: int, data_item: str) -> int:
        self._require_lock_manager().acquire(
            LockRequest(
                transaction_id=transaction_id,
                data_item=data_item,
                lock_type=LockType.SHARED,
            )
        )
        return self.repository.add_operation(transaction_id, "READ", data_item, utc_now())

    def write(self, transaction_id: int, data_item: str) -> int:
        self._require_lock_manager().acquire(
            LockRequest(
                transaction_id=transaction_id,
                data_item=data_item,
                lock_type=LockType.EXCLUSIVE,
            )
        )
        return self.repository.add_operation(transaction_id, "WRITE", data_item, utc_now())

    def commit(self, transaction_id: int) -> None:
        self.repository.finish(transaction_id, "COMMITTED", utc_now())
        self._require_lock_manager().release_all(transaction_id)

    def rollback(self, transaction_id: int) -> None:
        self.repository.finish(transaction_id, "ROLLED_BACK", utc_now())
        self._require_lock_manager().release_all(transaction_id)
