"""Deterministic wait-for graph and deadlock detection."""

from collections import defaultdict
from collections.abc import Iterable

from app.models.deadlocks import (
    DeadlockDetectionResult,
    LockSnapshot,
)
from app.models.locks import LockStatus, LockType


def _conflicts(waiting: LockSnapshot, held: LockSnapshot) -> bool:
    return waiting.lock_type == LockType.EXCLUSIVE or held.lock_type == LockType.EXCLUSIVE


def _canonical_cycle(cycle: list[int]) -> tuple[int, ...]:
    rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
    return min(rotations)


class DeadlockService:
    """Build a wait-for graph from lock rows and return all simple cycles."""

    def detect_deadlocks(self, locks: Iterable[LockSnapshot] = ()) -> list[list[int]]:
        result = self.detect(locks)
        return result.cycles

    def detect(self, locks: Iterable[LockSnapshot]) -> DeadlockDetectionResult:
        snapshots = list(locks)
        graph: dict[int, set[int]] = defaultdict(set)

        waiting = [lock for lock in snapshots if lock.status == LockStatus.WAITING]
        held = [lock for lock in snapshots if lock.status == LockStatus.HELD]
        for waiter in waiting:
            for holder in held:
                if (
                    waiter.transaction_id != holder.transaction_id
                    and waiter.data_item == holder.data_item
                    and _conflicts(waiter, holder)
                ):
                    graph[waiter.transaction_id].add(holder.transaction_id)

        cycles: set[tuple[int, ...]] = set()

        def visit(start: int, node: int, path: list[int]) -> None:
            for neighbor in sorted(graph.get(node, set())):
                if neighbor == start and len(path) > 1:
                    cycles.add(_canonical_cycle(path))
                elif neighbor not in path and len(path) < len(graph):
                    visit(start, neighbor, path + [neighbor])

        for start in sorted(graph):
            visit(start, start, [start])

        ordered_cycles = [list(cycle) for cycle in sorted(cycles)]
        return DeadlockDetectionResult(
            deadlock_detected=bool(ordered_cycles),
            wait_for_graph={
                str(transaction_id): sorted(neighbors)
                for transaction_id, neighbors in sorted(graph.items())
            },
            cycles=ordered_cycles,
        )
