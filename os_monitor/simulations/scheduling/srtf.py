"""
SRTF - Shortest Remaining Time First (Preemptive SJF)
At every unit of time, the process with the shortest remaining burst time runs.
If a new process arrives with shorter remaining time, it preempts the current process.
"""
from typing import List
from .fcfs import Process, SchedulerResult


def srtf(processes: List[Process]) -> SchedulerResult:
    """
    Shortest Remaining Time First (Preemptive SJF).
    Simulates tick-by-tick (1 unit of time per iteration).
    """
    procs = [Process(p.pid, p.arrival_time, p.burst_time, p.priority) for p in processes]
    n = len(procs)
    completed = []
    gantt = []

    current_time = 0
    done = 0
    prev_pid = -1

    while done < n:
        # Ready queue: arrived and not yet finished
        ready = [p for p in procs if p.arrival_time <= current_time and p.remaining_time > 0]

        if not ready:
            current_time += 1
            continue

        # Pick shortest remaining time; tie-break by arrival
        p = min(ready, key=lambda x: (x.remaining_time, x.arrival_time))

        if p.start_time == -1:
            p.start_time = current_time

        # Gantt: merge consecutive slices of same PID
        if gantt and gantt[-1]["pid"] == p.pid:
            gantt[-1]["end"] = current_time + 1
        else:
            gantt.append({"pid": p.pid, "start": current_time, "end": current_time + 1})

        p.remaining_time -= 1
        current_time += 1

        if p.remaining_time == 0:
            p.finish_time = current_time
            p.turnaround_time = p.finish_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            completed.append(p)
            done += 1

    total_time = current_time
    busy_time = sum(p.burst_time for p in completed)

    return SchedulerResult(
        algorithm="SRTF (Preemptive SJF)",
        processes=completed,
        gantt_chart=gantt,
        avg_waiting_time=sum(p.waiting_time for p in completed) / len(completed),
        avg_turnaround_time=sum(p.turnaround_time for p in completed) / len(completed),
        cpu_utilization=round((busy_time / total_time) * 100, 2) if total_time > 0 else 0,
        throughput=round(len(completed) / total_time, 4) if total_time > 0 else 0,
    )
