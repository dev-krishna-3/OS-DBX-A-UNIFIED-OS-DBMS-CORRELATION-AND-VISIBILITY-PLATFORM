"""
Priority Scheduling - Non-Preemptive
Lower priority number = Higher priority (like Linux nice values).
Among same-priority ready processes, FCFS is used as a tiebreaker.
"""
from typing import List
from .fcfs import Process, SchedulerResult


def priority_scheduling(processes: List[Process]) -> SchedulerResult:
    """
    Priority Scheduling (Non-Preemptive).
    At each dispatch point, select the ready process with the lowest priority number.
    """
    procs = [Process(p.pid, p.arrival_time, p.burst_time, p.priority) for p in processes]
    completed = []
    gantt = []
    current_time = 0
    remaining = procs[:]

    while remaining:
        ready = [p for p in remaining if p.arrival_time <= current_time]

        if not ready:
            current_time = min(p.arrival_time for p in remaining)
            continue

        # Pick lowest priority number; tie-break by arrival_time (FCFS)
        p = min(ready, key=lambda x: (x.priority, x.arrival_time))
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
        algorithm="Priority (Non-Preemptive)",
        processes=completed,
        gantt_chart=gantt,
        avg_waiting_time=sum(p.waiting_time for p in completed) / len(completed),
        avg_turnaround_time=sum(p.turnaround_time for p in completed) / len(completed),
        cpu_utilization=round((busy_time / total_time) * 100, 2) if total_time > 0 else 0,
        throughput=round(len(completed) / total_time, 4) if total_time > 0 else 0,
    )
