"""
SJF - Shortest Job First CPU Scheduling
Non-preemptive. Among all arrived processes, pick the one with shortest burst time.
"""
from typing import List
from .fcfs import Process, SchedulerResult


def sjf(processes: List[Process]) -> SchedulerResult:
    """
    Shortest Job First (Non-Preemptive).
    At each dispatch point, select the ready process with the minimum burst_time.
    """
    procs = [Process(p.pid, p.arrival_time, p.burst_time, p.priority) for p in processes]
    completed = []
    gantt = []
    current_time = 0
    remaining = procs[:]

    while remaining:
        # All processes that have arrived by current_time
        ready = [p for p in remaining if p.arrival_time <= current_time]

        if not ready:
            # CPU idle — jump to the next arriving process
            current_time = min(p.arrival_time for p in remaining)
            continue

        # Pick shortest burst time; tie-break by arrival time
        p = min(ready, key=lambda x: (x.burst_time, x.arrival_time))
        remaining.remove(p)

        p.start_time = current_time
        p.finish_time = current_time + p.burst_time
        p.turnaround_time = p.finish_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

        gantt.append({"pid": p.pid, "start": p.start_time, "end": p.finish_time})
        current_time = p.finish_time
        completed.append(p)

    total_time = current_time
    busy_time = sum(p.burst_time for p in completed)

    return SchedulerResult(
        algorithm="SJF",
        processes=completed,
        gantt_chart=gantt,
        avg_waiting_time=sum(p.waiting_time for p in completed) / len(completed),
        avg_turnaround_time=sum(p.turnaround_time for p in completed) / len(completed),
        cpu_utilization=round((busy_time / total_time) * 100, 2) if total_time > 0 else 0,
        throughput=round(len(completed) / total_time, 4) if total_time > 0 else 0,
    )
