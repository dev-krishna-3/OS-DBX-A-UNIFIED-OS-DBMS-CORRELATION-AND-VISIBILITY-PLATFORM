"""Tests for transaction and lock-manager integration."""

from datetime import datetime, timezone

import pytest

from app.models.locks import LockType
from app.services.transaction_service import TransactionService


class FakeTransactionRepository:
    def __init__(self, events):
        self.events = events

    def begin(self, pid, isolation_level, timestamp):
        self.events.append(("begin", pid, isolation_level, timestamp))
        return 12

    def add_operation(self, transaction_id, operation_type, data_item, timestamp):
        self.events.append(("operation", transaction_id, operation_type, data_item, timestamp))
        return 7

    def finish(self, transaction_id, status, timestamp):
        self.events.append(("finish", transaction_id, status, timestamp))


class FakeLockManager:
    def __init__(self, events):
        self.events = events

    def acquire(self, request):
        self.events.append(("acquire", request))

    def release_all(self, transaction_id):
        self.events.append(("release_all", transaction_id))


def make_service():
    events = []
    repository = FakeTransactionRepository(events)
    lock_manager = FakeLockManager(events)
    return TransactionService(repository, lock_manager), events


def test_begin_delegates_to_transaction_repository():
    service, events = make_service()

    transaction_id = service.begin(4211, "READ_COMMITTED")

    assert transaction_id == 12
    assert events[0][0:3] == ("begin", 4211, "READ_COMMITTED")
    assert events[0][3].tzinfo is None


def test_read_acquires_shared_lock_before_recording_read():
    service, events = make_service()

    assert service.read(12, "users:1") == 7

    assert events[0][0] == "acquire"
    assert events[0][1].transaction_id == 12
    assert events[0][1].data_item == "users:1"
    assert events[0][1].lock_type == LockType.SHARED
    assert events[1][0:4] == ("operation", 12, "READ", "users:1")
    assert not any(event[0] == "release_all" for event in events)


def test_write_acquires_exclusive_lock_before_recording_write():
    service, events = make_service()

    assert service.write(12, "users:1") == 7

    assert events[0][0] == "acquire"
    assert events[0][1].transaction_id == 12
    assert events[0][1].data_item == "users:1"
    assert events[0][1].lock_type == LockType.EXCLUSIVE
    assert events[1][0:4] == ("operation", 12, "WRITE", "users:1")
    assert not any(event[0] == "release_all" for event in events)


def test_commit_finishes_transaction_before_releasing_locks():
    service, events = make_service()

    service.commit(12)

    assert [event[0] for event in events] == ["finish", "release_all"]
    assert events[0][1:3] == (12, "COMMITTED")
    assert events[1] == ("release_all", 12)


def test_rollback_finishes_transaction_before_releasing_locks():
    service, events = make_service()

    service.rollback(12)

    assert [event[0] for event in events] == ["finish", "release_all"]
    assert events[0][1:3] == (12, "ROLLED_BACK")
    assert events[1] == ("release_all", 12)


def test_locks_are_not_released_during_read_or_write():
    service, events = make_service()

    service.read(12, "users:1")
    service.write(12, "users:2")

    assert [event[0] for event in events] == [
        "acquire",
        "operation",
        "acquire",
        "operation",
    ]
    assert all(event[0] != "release_all" for event in events)


@pytest.mark.parametrize("operation", ["read", "write"])
def test_read_and_write_require_a_lock_manager(operation):
    events = []
    service = TransactionService(FakeTransactionRepository(events))

    with pytest.raises(RuntimeError, match="LockManager"):
        getattr(service, operation)(12, "users:1")

    assert events == []


def test_transaction_timestamps_are_utc_naive():
    service, events = make_service()

    service.begin(4211, "READ_COMMITTED")
    service.read(12, "users:1")
    service.write(12, "users:2")
    service.commit(12)

    for event in events:
        timestamp = event[-1]
        if isinstance(timestamp, datetime):
            assert timestamp.tzinfo is None


def test_utc_now_is_close_to_current_utc_time():
    from app.services.transaction_service import utc_now

    before = datetime.now(timezone.utc).replace(tzinfo=None)
    timestamp = utc_now()
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert before <= timestamp <= after
