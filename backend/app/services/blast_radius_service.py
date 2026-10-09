"""Service for computing deterministic blast-radius impact of incidents."""

from app.models.blast_radius import (
    AffectedResource,
    BlastRadiusResult,
    ImpactEvidence,
    ImpactLevel,
    ResourceType,
)
from app.services.deadlock_service import DeadlockService
from app.services.lock_manager import LockManager
from app.services.transaction_service import TransactionService


class BlastRadiusService:
    """Analyzes the direct and indirect impact of an incident."""

    def __init__(
        self,
        deadlock_service: DeadlockService,
        lock_manager: LockManager,
        transaction_service: TransactionService,
    ):
        self.deadlock_service = deadlock_service
        self.lock_manager = lock_manager
        self.transaction_service = transaction_service

    def analyze_deadlock_incident(self, incident_id: int) -> BlastRadiusResult:
        """Analyze the blast radius of a deadlock incident deterministically."""
        resources = []
        cycle_tx_ids = set()
        
        # 1. Try detect_deadlocks() method on deadlock_service if available
        deadlocks = None
        detect_dl_fn = getattr(self.deadlock_service, "detect_deadlocks", None)
        if callable(detect_dl_fn):
            try:
                deadlocks = detect_dl_fn()
            except Exception:
                pass

        if deadlocks and isinstance(deadlocks, list):
            for item in deadlocks:
                cycle_edges = getattr(item, "cycle", [])
                if isinstance(cycle_edges, list):
                    for edge in cycle_edges:
                        waiting_tx = getattr(edge, "waiting_tx", None)
                        holding_tx = getattr(edge, "holding_tx", None)
                        data_item = getattr(edge, "data_item", None)
                        if waiting_tx is not None:
                            cycle_tx_ids.add(waiting_tx)
                            resources.append(
                                AffectedResource(
                                    resource_type=ResourceType.TRANSACTION,
                                    resource_id=str(waiting_tx),
                                    impact_level=ImpactLevel.DIRECT,
                                    evidence=ImpactEvidence(
                                        rule_applied="DEADLOCK_CYCLE_MEMBER",
                                        relationship="Transaction is waiting in the deadlock cycle."
                                    )
                                )
                            )
                        if holding_tx is not None:
                            cycle_tx_ids.add(holding_tx)
                        if data_item is not None:
                            resources.append(
                                AffectedResource(
                                    resource_type=ResourceType.LOCK,
                                    resource_id=str(data_item),
                                    impact_level=ImpactLevel.DIRECT,
                                    evidence=ImpactEvidence(
                                        rule_applied="DEADLOCK_CYCLE_RESOURCE",
                                        relationship="Lock is contended in the deadlock cycle."
                                    )
                                )
                            )

        # 2. Also check lock_manager.get_all_locks if present
        get_locks = getattr(self.lock_manager, "get_all_locks", None)
        if callable(get_locks):
            locks = get_locks()
            detection = self.deadlock_service.detect(locks)
            if detection.cycles:
                for cycle in detection.cycles:
                    for tx in cycle:
                        cycle_tx_ids.add(tx)
                        resources.append(
                            AffectedResource(
                                resource_type=ResourceType.TRANSACTION,
                                resource_id=str(tx),
                                impact_level=ImpactLevel.DIRECT,
                                evidence=ImpactEvidence(
                                    rule_applied="DEADLOCK_CYCLE_MEMBER",
                                    relationship="Transaction is involved in the deadlock cycle."
                                )
                            )
                        )

        # 3. INDIRECT impact (wait_for_graph)
        wait_graph = getattr(self.lock_manager, "wait_for_graph", {})
        if wait_graph and isinstance(wait_graph, dict):
            for wait_node in wait_graph:
                if wait_node not in cycle_tx_ids:
                    resources.append(
                        AffectedResource(
                            resource_type=ResourceType.TRANSACTION,
                            resource_id=str(wait_node),
                            impact_level=ImpactLevel.INDIRECT,
                            evidence=ImpactEvidence(
                                rule_applied="BLOCKED_BY_CYCLE",
                                relationship="Transaction is indirectly blocked."
                            )
                        )
                    )

        # 4. POTENTIAL impact (active txs)
        get_active_txs = getattr(self.transaction_service, "get_active_transactions", None)
        if callable(get_active_txs):
            try:
                active_txs = get_active_txs()
                for tx_id in active_txs:
                    if tx_id not in cycle_tx_ids:
                        resources.append(
                            AffectedResource(
                                resource_type=ResourceType.TRANSACTION,
                                resource_id=str(tx_id),
                                impact_level=ImpactLevel.POTENTIAL,
                                evidence=ImpactEvidence(
                                    rule_applied="ACTIVE_DURING_INCIDENT",
                                    relationship="Transaction is active while incident is unresolved."
                                )
                            )
                        )
            except Exception:
                pass

        unique_resources = {}
        for r in resources:
            key = f"{r.resource_type.value}:{r.resource_id}"
            if key not in unique_resources or unique_resources[key].impact_level != ImpactLevel.DIRECT:
                unique_resources[key] = r

        return BlastRadiusResult(
            incident_id=incident_id,
            incident_type="DEADLOCK",
            affected_resources=list(unique_resources.values())
        )
