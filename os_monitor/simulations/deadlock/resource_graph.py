"""
Resource Allocation Graph (RAG) - Deadlock Detection
Detects deadlock by looking for cycles in the resource allocation graph.

Nodes: Processes (P) and Resources (R)
Edges:
  - Assignment Edge:  R -> P  (resource R is allocated to process P)
  - Request Edge:     P -> R  (process P is waiting for resource R)

A cycle in the RAG (with single-instance resources) = deadlock.
"""
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple


@dataclass
class RAGResult:
    deadlock_detected: bool
    deadlocked_processes: List[int]   # PIDs stuck in deadlock
    cycle: List[str]                  # Cycle path e.g. ["P0", "R1", "P1", "R0", "P0"]
    reason: str


def detect_deadlock(
    processes: List[int],
    resources: List[int],
    allocation: Dict[int, List[int]],    # allocation[pid] = [r1, r2, ...] list of held resource IDs
    request: Dict[int, List[int]],       # request[pid] = [r1, r2, ...] list of waited resource IDs
) -> RAGResult:
    """
    Deadlock Detection via Resource Allocation Graph cycle detection.
    Works for single-instance resources.
    
    allocation: {pid: [resource_ids currently held]}
    request:    {pid: [resource_ids currently waiting for]}
    """

    # Build adjacency list for RAG
    # Nodes: "P{pid}" for processes, "R{rid}" for resources
    graph: Dict[str, Set[str]] = {}
    
    for p in processes:
        graph[f"P{p}"] = set()
    for r in resources:
        graph[f"R{r}"] = set()

    # Request edges: P -> R
    for pid, res_list in request.items():
        for rid in res_list:
            graph[f"P{pid}"].add(f"R{rid}")

    # Assignment edges: R -> P
    for pid, res_list in allocation.items():
        for rid in res_list:
            graph[f"R{rid}"].add(f"P{pid}")

    # Cycle detection using DFS
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    cycle_path: List[str] = []

    def dfs(node: str, path: List[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, path):
                    return True
            elif neighbor in rec_stack:
                # Found cycle — record it
                cycle_start = path.index(neighbor)
                cycle_path.extend(path[cycle_start:] + [neighbor])
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    for node in list(graph.keys()):
        if node not in visited:
            if dfs(node, []):
                break

    deadlocked = []
    if cycle_path:
        # Extract PIDs from cycle
        for node in cycle_path:
            if node.startswith("P"):
                pid = int(node[1:])
                if pid not in deadlocked:
                    deadlocked.append(pid)

    return RAGResult(
        deadlock_detected=bool(cycle_path),
        deadlocked_processes=deadlocked,
        cycle=cycle_path,
        reason=(
            f"Deadlock detected! Cycle: {' -> '.join(cycle_path)}. PIDs involved: {deadlocked}"
            if cycle_path
            else "No deadlock detected. The resource allocation graph is acyclic."
        )
    )
