"""
Multi-Level Feedback Queue (MLFQ) CPU Scheduling Algorithm.
Features 3 Priority Queues:
- Queue 0: Highest priority, Round Robin (Quantum = q)
- Queue 1: Medium priority, Round Robin (Quantum = 2 * q)
- Queue 2: Lowest priority, First-Come-First-Served (FCFS)
Processes demote upon consuming full queue time quantum.
"""
from typing import List, Dict, Any
from os_monitor.simulations.scheduling.fcfs import Process, SchedulerResult


def mlfq(processes: List[Process], quantum: int = 2) -> SchedulerResult:
    """
    Deterministic Multi-Level Feedback Queue scheduling simulation.
    """
    if not processes:
        return SchedulerResult(
            algorithm="MLFQ",
            processes=[],
            gantt_chart=[],
            avg_waiting_time=0.0,
            avg_turnaround_time=0.0,
            cpu_utilization=0.0,
            throughput=0.0,
        )

    procs = [
        Process(
            pid=p.pid,
            arrival_time=p.arrival_time,
            burst_time=p.burst_time,
            priority=p.priority,
        )
        for p in processes
    ]
    # Reset tracking
    for p in procs:
        p.remaining_time = p.burst_time
        p.start_time = -1
        p.finish_time = 0

    q0_quantum = max(1, quantum)
    q1_quantum = q0_quantum * 2

    # Queues store process indices
    q0: List[int] = []
    q1: List[int] = []
    q2: List[int] = []

    time = 0
    completed = 0
    n = len(procs)
    gantt: List[Dict[str, Any]] = []

    # Sort arrival tracking
    arrived_indices = set()

    def check_arrivals(current_time: int):
        for idx, p in enumerate(procs):
            if idx not in arrived_indices and p.arrival_time <= current_time:
                arrived_indices.add(idx)
                q0.append(idx)

    # Prime initial arrivals
    min_arr = min(p.arrival_time for p in procs)
    if time < min_arr:
        time = min_arr
    check_arrivals(time)

    while completed < n:
        if not q0 and not q1 and not q2:
            # CPU is idle, jump to next arrival
            unArrived = [p.arrival_time for idx, p in enumerate(procs) if idx not in arrived_indices]
            if unArrived:
                time = min(unArrived)
                check_arrivals(time)
            else:
                break

        # Priority 0
        if q0:
            idx = q0.pop(0)
            p = procs[idx]
            if p.start_time == -1:
                p.start_time = time
            run_time = min(p.remaining_time, q0_quantum)
            start_t = time
            time += run_time
            p.remaining_time -= run_time
            gantt.append({"pid": p.pid, "start": start_t, "end": time})
            check_arrivals(time)
            if p.remaining_time == 0:
                p.finish_time = time
                completed += 1
            else:
                # Demoted to Q1
                q1.append(idx)
            continue

        # Priority 1
        if q1:
            idx = q1.pop(0)
            p = procs[idx]
            if p.start_time == -1:
                p.start_time = time
            run_time = min(p.remaining_time, q1_quantum)
            start_t = time
            time += run_time
            p.remaining_time -= run_time
            gantt.append({"pid": p.pid, "start": start_t, "end": time})
            check_arrivals(time)
            if p.remaining_time == 0:
                p.finish_time = time
                completed += 1
            else:
                # Demoted to Q2
                q2.append(idx)
            continue

        # Priority 2 (FCFS)
        if q2:
            idx = q2.pop(0)
            p = procs[idx]
            if p.start_time == -1:
                p.start_time = time
            run_time = p.remaining_time
            start_t = time
            time += run_time
            p.remaining_time = 0
            p.finish_time = time
            gantt.append({"pid": p.pid, "start": start_t, "end": time})
            check_arrivals(time)
            completed += 1
            continue

    # Compact gantt chart (merge consecutive identical pids)
    merged_gantt: List[Dict[str, Any]] = []
    for slice_entry in gantt:
        if merged_gantt and merged_gantt[-1]["pid"] == slice_entry["pid"] and merged_gantt[-1]["end"] == slice_entry["start"]:
            merged_gantt[-1]["end"] = slice_entry["end"]
        else:
            merged_gantt.append(dict(slice_entry))

    # Calculate metrics
    for p in procs:
        p.turnaround_time = p.finish_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

    busy_time = sum(p.burst_time for p in procs)
    avg_wait = sum(p.waiting_time for p in procs) / n if n > 0 else 0.0
    avg_turnaround = sum(p.turnaround_time for p in procs) / n if n > 0 else 0.0

    return SchedulerResult(
        algorithm="MLFQ",
        processes=procs,
        gantt_chart=merged_gantt,
        avg_waiting_time=round(avg_wait, 2),
        avg_turnaround_time=round(avg_turnaround, 2),
        cpu_utilization=round((busy_time / time) * 100, 2) if time > 0 else 0.0,
        throughput=round(n / time, 4) if time > 0 else 0.0,
    )
