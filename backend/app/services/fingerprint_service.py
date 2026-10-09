"""Service for computing deterministic structural fingerprints of incidents."""

import hashlib

from app.models.fingerprint import IncidentFingerprint


class FingerprintService:
    """Computes deterministic fingerprints without ML/AI."""

    def fingerprint_deadlock(self, cycle: list[int]) -> IncidentFingerprint:
        """Create a fingerprint for a deadlock cycle.
        
        A structural deadlock fingerprint depends on the shape of the cycle
        (number of transactions).
        """
        # Sort transaction IDs to create a deterministic mapping
        sorted_txs = sorted(list(set(cycle)))
        tx_map = {tx: f"T{i}" for i, tx in enumerate(sorted_txs)}
        
        normalized_edges = []
        # Cycle is a list of nodes, e.g., [1, 2, 3] means 1 waits on 2, 2 on 3, 3 on 1.
        for i in range(len(cycle)):
            waiting = cycle[i]
            holding = cycle[(i + 1) % len(cycle)]
            normalized_edges.append(f"{tx_map[waiting]}->{tx_map[holding]}")
            
        # Sort edges to ensure cycle starting point doesn't change the hash
        normalized_edges.sort()
        
        structure_str = f"DEADLOCK-TX{len(sorted_txs)}-[" + "|".join(normalized_edges) + "]"
        
        hash_obj = hashlib.sha256(structure_str.encode('utf-8'))
        
        return IncidentFingerprint(
            incident_type="DEADLOCK",
            transaction_count=len(sorted_txs),
            lock_count=len(sorted_txs), # Approximately 1 lock contention per wait edge
            normalized_structure=structure_str,
            deterministic_hash=hash_obj.hexdigest()
        )
