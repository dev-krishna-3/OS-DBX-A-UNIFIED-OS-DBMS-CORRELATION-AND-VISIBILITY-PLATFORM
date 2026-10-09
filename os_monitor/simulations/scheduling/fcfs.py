"""
FCFS - First Come First Serve CPU Scheduling
Non-preemptive. Processes are executed in the order they arrive.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Process:
    pid: int
    arrival_time: int
    burst_time: int
    priority: int = 0          # Used by Priority Scheduling
    remaining_time: int = 0    # Used by SRTF / Round Robin
    start_time: int = -1
    finish_time: int = 0
    waiting_time: int = 0
    turnaround_time: int = 0

    def __post_init__(self):
        self.remaining_time = self.burst_time


@dataclass
class SchedulerResult:
    algorithm: str
    processes: List[Process]
    gantt_chart: List[dict]    # [{"pid": 1, "start": 0, "end": 3}, ...]
    avg_waiting_time: float
    avg_turnaround_time: float
    cpu_utilization: float
    throughput: float


def fcfs(processes: List[Process]) -> SchedulerResult:
    """
    First Come First Serve Scheduling.
    Non-preemptive. Sorted by arrival_time.
    """
    procs = sorted(processes, key=lambda p: p.arrival_time)
    gantt = []
    current_time = 0

    for p in procs:
        if current_time < p.arrival_time:
            current_time = p.arrival_time  # CPU idle gap

        p.start_time = current_time
        p.finish_time = current_time + p.burst_time
        p.turnaround_time = p.finish_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

        gantt.append({"pid": p.pid, "start": p.start_time, "end": p.finish_time})
        current_time = p.finish_time

    total_time = current_time
    busy_time = sum(p.burst_time for p in procs)

    return SchedulerResult(
        algorithm="FCFS",
        processes=procs,
        gantt_chart=gantt,
        avg_waiting_time=sum(p.waiting_time for p in procs) / len(procs),
        avg_turnaround_time=sum(p.turnaround_time for p in procs) / len(procs),
        cpu_utilization=round((busy_time / total_time) * 100, 2) if total_time > 0 else 0,
        throughput=round(len(procs) / total_time, 4) if total_time > 0 else 0,
    )
