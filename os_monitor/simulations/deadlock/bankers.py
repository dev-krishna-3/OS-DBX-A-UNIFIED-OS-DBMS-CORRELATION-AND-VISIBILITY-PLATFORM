"""
Banker's Algorithm - Deadlock Avoidance
Determines if granting a resource request leaves the system in a SAFE state.
A safe state is one where there exists a safe sequence of process execution
such that all processes can eventually get all resources they need.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BankersResult:
    is_safe: bool
    safe_sequence: List[int]       # PIDs in safe execution order
    reason: str                    # Explanation of the verdict


def bankers_algorithm(
    allocation: List[List[int]],   # allocation[i][j] = resources of type j held by process i
    max_need: List[List[int]],     # max_need[i][j] = max resources of type j process i may ever need
    available: List[int],          # available[j] = currently available units of resource type j
    request: Optional[List[int]] = None,   # Optional: new request from process 0
    requesting_pid: int = 0
) -> BankersResult:
    """
    Banker's Algorithm.
    If `request` is provided, first checks if granting it keeps the system safe.
    """
    n = len(allocation)   # number of processes
    m = len(available)    # number of resource types

    # Calculate need matrix: need[i][j] = max_need[i][j] - allocation[i][j]
    need = [[max_need[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]

    # ---- Resource Request Simulation (if provided) ----
    if request is not None:
        pid = requesting_pid
        # Check 1: Request <= Need
        if any(request[j] > need[pid][j] for j in range(m)):
            return BankersResult(
                is_safe=False,
                safe_sequence=[],
                reason=f"Process {pid} requested more than its declared maximum need."
            )
        # Check 2: Request <= Available
        if any(request[j] > available[j] for j in range(m)):
            return BankersResult(
                is_safe=False,
                safe_sequence=[],
                reason=f"Process {pid} must wait. Resources not currently available."
            )
        # Tentatively allocate
        for j in range(m):
            available[j] -= request[j]
            allocation[pid][j] += request[j]
            need[pid][j] -= request[j]

    # ---- Safety Algorithm ----
    work = available[:]
    finish = [False] * n
    safe_sequence = []

    while len(safe_sequence) < n:
        found = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                # Process i can complete with current work
                for j in range(m):
                    work[j] += allocation[i][j]
                finish[i] = True
                safe_sequence.append(i)
                found = True
                break

        if not found:
            return BankersResult(
                is_safe=False,
                safe_sequence=[],
                reason="System is in an UNSAFE state. No safe sequence found. Deadlock possible."
            )

    return BankersResult(
        is_safe=True,
        safe_sequence=safe_sequence,
        reason=f"System is in a SAFE state. Safe sequence: {safe_sequence}"
    )
