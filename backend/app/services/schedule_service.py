"""Conflict-serializability analysis for the DBMS Simulation Lab."""

from collections import defaultdict

from app.models.schedules import ScheduleAnalysisResult, ScheduleOperation


def _canonical_cycle(cycle: list[int]) -> tuple[int, ...]:
    rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
    return min(rotations)


class ScheduleService:
    def analyze(self, operations: list[ScheduleOperation]) -> ScheduleAnalysisResult:
        graph: dict[int, set[int]] = defaultdict(set)
        for index, left in enumerate(operations):
            for right in operations[index + 1 :]:
                if (
                    left.transaction_id != right.transaction_id
                    and left.data_item == right.data_item
                    and (left.operation == "W" or right.operation == "W")
                ):
                    graph[left.transaction_id].add(right.transaction_id)

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
        return ScheduleAnalysisResult(
            conflict_serializable=not ordered_cycles,
            precedence_graph={
                str(transaction_id): sorted(neighbors)
                for transaction_id, neighbors in sorted(graph.items())
            },
            cycles=ordered_cycles,
        )
