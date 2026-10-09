from app.models.deadlocks import LockSnapshot
from app.services.deadlock_service import DeadlockService


def test_detects_two_transaction_wait_for_cycle():
    result = DeadlockService().detect(
        [
            LockSnapshot(transaction_id=1, data_item="A", lock_type="X", status="HELD"),
            LockSnapshot(transaction_id=2, data_item="B", lock_type="X", status="HELD"),
            LockSnapshot(transaction_id=1, data_item="B", lock_type="X", status="WAITING"),
            LockSnapshot(transaction_id=2, data_item="A", lock_type="X", status="WAITING"),
        ]
    )

    assert result.deadlock_detected
    assert result.wait_for_graph == {"1": [2], "2": [1]}
    assert result.cycles == [[1, 2]]


def test_shared_locks_do_not_create_a_wait_edge():
    result = DeadlockService().detect(
        [
            LockSnapshot(transaction_id=1, data_item="A", lock_type="S", status="HELD"),
            LockSnapshot(transaction_id=2, data_item="A", lock_type="S", status="WAITING"),
        ]
    )

    assert not result.deadlock_detected
    assert result.wait_for_graph == {}
