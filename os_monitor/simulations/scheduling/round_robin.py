"""
Round Robin CPU Scheduling
Preemptive. Each process gets a fixed time quantum. Unfinshed processes
are placed back at the end of the ready queue.
"""
from typing import List
from collections import deque
from .fcfs import Process, SchedulerResult


def round_robin(processes: List[Process], quantum: int = 2) -> SchedulerResult:
    """
    Round Robin Scheduling.
    quantum: time slice each process gets before being preempted.
    """
    procs = {p.pid: Process(p.pid, p.arrival_time, p.burst_time, p.priority)
             for p in processes}

    # Sort by arrival time for initial queue filling
    sorted_procs = sorted(procs.values(), key=lambda p: p.arrival_time)

    gantt = []
    current_time = 0
    queue = deque()
    remaining = sorted_procs[:]
    completed = []

    # Seed with processes arriving at time 0
    for p in remaining[:]:
        if p.arrival_time <= current_time:
            queue.append(p)
            remaining.remove(p)

    while queue or remaining:
        if not queue:
            # CPU idle
            current_time = remaining[0].arrival_time
            for p in remaining[:]:
                if p.arrival_time <= current_time:
                    queue.append(p)
                    remaining.remove(p)

        p = queue.popleft()

        if p.start_time == -1:
            p.start_time = current_time

        # Determine how long this slice runs
        run_time = min(quantum, p.remaining_time)
        gantt.append({"pid": p.pid, "start": current_time, "end": current_time + run_time})
        current_time += run_time
        p.remaining_time -= run_time

        # Enqueue newly arrived processes during this time slice
        for rp in remaining[:]:
            if rp.arrival_time <= current_time:
                queue.append(rp)
                remaining.remove(rp)

        if p.remaining_time == 0:
            p.finish_time = current_time
            p.turnaround_time = p.finish_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            completed.append(p)
        else:
            queue.append(p)  # Re-queue unfinished process

    total_time = current_time
    busy_time = sum(p.burst_time for p in completed)

    return SchedulerResult(
        algorithm=f"Round Robin (Q={quantum})",
        processes=completed,
        gantt_chart=gantt,
        avg_waiting_time=sum(p.waiting_time for p in completed) / len(completed),
        avg_turnaround_time=sum(p.turnaround_time for p in completed) / len(completed),
        cpu_utilization=round((busy_time / total_time) * 100, 2) if total_time > 0 else 0,
        throughput=round(len(completed) / total_time, 4) if total_time > 0 else 0,
    )
