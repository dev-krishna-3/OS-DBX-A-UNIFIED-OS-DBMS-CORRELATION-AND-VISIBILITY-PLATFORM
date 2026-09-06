"""Tests for the lock manager and Strict 2PL lifecycle."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.locks import LockRequest
from app.repositories.lock_repository import LockRepository
from app.repositories.transaction_repository import TransactionNotFoundError
from app.services.lock_manager import LockManager
from app.services.transaction_service import TransactionService


class FakeLockCursor:
    def __init__(self, database):
        self.database = database
        self.one = None
        self.many = []
        self.lastrowid = None
        self.rowcount = 0

    def execute(self, query, parameters):
        normalized = " ".join(query.split()).upper()
        self.rowcount = 0
        if normalized.startswith("SELECT STATUS FROM TRANSACTIONS"):
            transaction_id = parameters[0]
            status = self.database.transactions.get(transaction_id)
            self.one = None if status is None else {"status": status}
        elif normalized.startswith("SELECT LOCK_ID, TRANSACTION_ID"):
            data_item, status = parameters
            self.many = [
                lock.copy()
                for lock in self.database.locks
                if lock["data_item"] == data_item and lock["status"] == status
            ]
        elif normalized.startswith("INSERT INTO LOCKS"):
            transaction_id, data_item, lock_type, status, acquired_at, released_at = parameters
            self.lastrowid = self.database.next_lock_id
            self.database.next_lock_id += 1
            self.database.locks.append(
                {
                    "lock_id": self.lastrowid,
                    "transaction_id": transaction_id,
                    "data_item": data_item,
                    "lock_type": lock_type,
                    "status": status,
                    "acquired_at": acquired_at,
                    "released_at": released_at,
                }
            )
            self.rowcount = 1
        elif normalized.startswith("UPDATE LOCKS SET LOCK_TYPE"):
            lock_type, lock_id, status = parameters
            for lock in self.database.locks:
                if lock["lock_id"] == lock_id and lock["status"] == status:
                    lock["lock_type"] = lock_type
                    self.rowcount = 1
        elif normalized.startswith("UPDATE LOCKS SET STATUS"):
            status, released_at, transaction_id, held_status, waiting_status = parameters
            for lock in self.database.locks:
                if (
                    lock["transaction_id"] == transaction_id
                    and lock["status"] in (held_status, waiting_status)
                ):
                    lock["status"] = status
                    lock["released_at"] = released_at
                    self.rowcount += 1

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many

    def close(self):
        pass


class FakeLockDatabase:
    def __init__(self):
        self.transactions = {1: "ACTIVE", 2: "ACTIVE", 3: "ACTIVE"}
        self.locks = []
        self.next_lock_id = 1
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return FakeLockCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def request(transaction_id, lock_type, data_item="users:1"):
    return LockRequest(
        transaction_id=transaction_id,
        data_item=data_item,
        lock_type=lock_type,
    )


@pytest.fixture
def database():
    return FakeLockDatabase()


@pytest.fixture
def manager(database):
    return LockManager(LockRepository(database))


def test_shared_lock_is_held(manager):
    result = manager.acquire(request(1, "S"))

    assert result.lock_type == "S"
    assert result.status == "HELD"


def test_exclusive_lock_is_held(manager):
    result = manager.acquire(request(1, "X"))

    assert result.lock_type == "X"
    assert result.status == "HELD"


def test_compatible_shared_locks_are_allowed(manager):
    first = manager.acquire(request(1, "S"))
    second = manager.acquire(request(2, "S"))

    assert first.status == "HELD"
    assert second.status == "HELD"
    assert first.lock_id != second.lock_id


def test_shared_and_exclusive_locks_conflict(manager):
    manager.acquire(request(1, "S"))

    result = manager.acquire(request(2, "X"))

    assert result.status == "WAITING"


def test_exclusive_and_shared_locks_conflict(manager):
    manager.acquire(request(1, "X"))

    result = manager.acquire(request(2, "S"))

    assert result.status == "WAITING"


def test_exclusive_locks_conflict_with_each_other(manager):
    manager.acquire(request(1, "X"))

    result = manager.acquire(request(2, "X"))

    assert result.status == "WAITING"


def test_same_transaction_reuses_and_can_upgrade_its_lock(manager, database):
    first = manager.acquire(request(1, "S"))
    same_lock = manager.acquire(request(1, "S"))
    upgraded = manager.acquire(request(1, "X"))

    assert same_lock.lock_id == first.lock_id
    assert upgraded.lock_id == first.lock_id
    assert upgraded.lock_type == "X"
    assert len(database.locks) == 1


class FakeTransactionRepository:
    def __init__(self, calls):
        self.calls = calls

    def finish(self, transaction_id, status, timestamp):
        self.calls.append(("finish", transaction_id, status))


def test_locks_are_released_after_commit_and_rollback(database):
    manager = LockManager(LockRepository(database))
    manager.acquire(request(1, "S"))
    calls = []
    service = TransactionService(FakeTransactionRepository(calls), manager)

    assert database.locks[0]["status"] == "HELD"
    service.commit(1)

    assert calls == [("finish", 1, "COMMITTED")]
    assert database.locks[0]["status"] == "RELEASED"
    assert database.locks[0]["released_at"].tzinfo is None

    manager.acquire(request(2, "X"))
    service.rollback(2)

    assert database.locks[1]["status"] == "RELEASED"


def test_invalid_transaction_is_rejected(database):
    with pytest.raises(TransactionNotFoundError):
        LockManager(LockRepository(database)).acquire(request(99, "S"))

    assert database.locks == []
    assert database.rollbacks == 1


def test_invalid_lock_request_is_rejected():
    with pytest.raises(ValidationError):
        LockRequest(transaction_id=0, data_item=" ", lock_type="INVALID")


def test_lock_timestamps_are_utc_naive_for_mysql(manager):
    result = manager.acquire(request(1, "S"))
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    assert result.acquired_at is not None
    assert result.acquired_at <= before
    assert result.acquired_at.tzinfo is None
