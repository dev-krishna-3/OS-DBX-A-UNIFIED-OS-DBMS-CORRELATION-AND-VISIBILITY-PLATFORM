"""Tests for benchmark, blast radius, and fingerprinting features."""

from app.models.benchmark import BenchmarkConfig, BenchmarkScenarioType
from app.models.blast_radius import ImpactLevel, ResourceType
from app.services.benchmark_service import BenchmarkRunnerService
from app.services.blast_radius_service import BlastRadiusService
from app.services.deadlock_service import DeadlockService
from app.services.fingerprint_service import FingerprintService
from app.services.lock_manager import LockManager
from app.services.transaction_service import TransactionService
from app.models.deadlocks import LockSnapshot
from app.models.locks import LockStatus, LockType


class MockLockManager:
    def acquire(self, request): pass
    def release_all(self, tx_id): pass

class MockTransactionService:
    def __init__(self):
        self.lock_manager = MockLockManager()
    def begin_transaction(self): return 1
    def commit_transaction(self, tx_id): pass

def test_benchmark_dbms_only():
    tx_service = MockTransactionService()
    runner = BenchmarkRunnerService(tx_service, tx_service.lock_manager)
    
    config = BenchmarkConfig(
        scenario=BenchmarkScenarioType.DBMS_ONLY,
        operations=5,
        concurrency=1
    )
    result = runner.run_benchmark(config)
    assert result.metrics.successful_operations == 5
    assert result.metrics.events_captured == 5


def test_fingerprint_deadlock():
    service = FingerprintService()
    # Cycle 1 waits on 2, 2 waits on 1
    cycle = [1, 2]
    fingerprint1 = service.fingerprint_deadlock(cycle)
    
    # Same cycle, different order: 2 waits on 1, 1 waits on 2
    cycle2 = [2, 1]
    fingerprint2 = service.fingerprint_deadlock(cycle2)
    
    assert fingerprint1.transaction_count == 2
    assert fingerprint1.lock_count == 2
    assert fingerprint1.incident_type == "DEADLOCK"
    assert fingerprint1.deterministic_hash == fingerprint2.deterministic_hash


def test_blast_radius():
    lock_manager = MockLockManager()
    tx_service = MockTransactionService()
    
    # Mocking deadlock_service that can be instantiated without LockManager
    class MockDeadlockService:
        def detect_deadlocks(self): return []
    
    deadlock_service = MockDeadlockService()
    
    blast_service = BlastRadiusService(
        deadlock_service=deadlock_service,
        lock_manager=lock_manager,
        transaction_service=tx_service
    )
    
    # Create a deadlock scenario
    locks = [
        LockSnapshot(transaction_id=1, data_item="A", lock_type=LockType.EXCLUSIVE, status=LockStatus.HELD),
        LockSnapshot(transaction_id=2, data_item="A", lock_type=LockType.EXCLUSIVE, status=LockStatus.WAITING),
        LockSnapshot(transaction_id=2, data_item="B", lock_type=LockType.EXCLUSIVE, status=LockStatus.HELD),
        LockSnapshot(transaction_id=1, data_item="B", lock_type=LockType.EXCLUSIVE, status=LockStatus.WAITING)
    ]
    
    try:
        deadlock_service.detect_deadlocks = lambda: [
            type('MockDeadlock', (), {'cycle': [
                type('MockEdge', (), {'waiting_tx': 1, 'holding_tx': 2, 'data_item': 'B', 'requested_mode': LockType.EXCLUSIVE, 'held_mode': LockType.EXCLUSIVE}),
                type('MockEdge', (), {'waiting_tx': 2, 'holding_tx': 1, 'data_item': 'A', 'requested_mode': LockType.EXCLUSIVE, 'held_mode': LockType.EXCLUSIVE})
            ]})
        ]
        
        # We need to mock active transactions for POTENTIAL impact to avoid errors
        tx_service.get_active_transactions = lambda: [1, 2, 3]
        lock_manager.wait_for_graph = {3: {2: ["C"]}}
        
        result = blast_service.analyze_deadlock_incident(incident_id=123)
        
        assert result.incident_id == 123
        assert result.direct_impact_count == 4 # TX 1, TX 2, Lock A, Lock B
        assert len(result.affected_resources) > 0
    finally:
        pass
