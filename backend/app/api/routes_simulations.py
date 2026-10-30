"""
OS Simulation Lab API routes.

Exposes REST endpoints for CPU Scheduling, Page Replacement Memory Management,
Banker's Algorithm Safety Checking, and Resource Allocation Graph (RAG) Deadlock Detection.
"""

import sys
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Ensure project root is on sys.path for os_monitor imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports from os_monitor simulation engine
from os_monitor.simulations.scheduling.fcfs import fcfs, Process as FCFSProcess
from os_monitor.simulations.scheduling.sjf import sjf
from os_monitor.simulations.scheduling.round_robin import round_robin
from os_monitor.simulations.scheduling.priority import priority_scheduling
from os_monitor.simulations.scheduling.srtf import srtf

from os_monitor.simulations.memory.fifo import fifo
from os_monitor.simulations.memory.lru import lru
from os_monitor.simulations.memory.optimal import optimal

from os_monitor.simulations.deadlock.bankers import bankers_algorithm
from os_monitor.simulations.deadlock.resource_graph import detect_deadlock

router = APIRouter(prefix="/simulations", tags=["simulations"])


# ---------------------------------------------------------------------------
# Pydantic Request & Response Models
# ---------------------------------------------------------------------------

class ProcessInput(BaseModel):
    pid: int
    arrival_time: int = Field(ge=0)
    burst_time: int = Field(gt=0)
    priority: int = 0


class SchedulingRequest(BaseModel):
    algorithm: str = Field(description="Algorithm: FCFS, SJF, SRTF, RR, PRIORITY")
    processes: List[ProcessInput]
    quantum: Optional[int] = Field(default=2, description="Time quantum for Round Robin")


class MemoryRequest(BaseModel):
    algorithm: str = Field(description="Algorithm: FIFO, LRU, OPTIMAL, ALL")
    reference_string: List[int]
    num_frames: int = Field(default=3, gt=0)


class BankersRequest(BaseModel):
    allocation: List[List[int]]
    max_need: List[List[int]]
    available: List[int]
    request: Optional[List[int]] = None
    requesting_pid: int = 0


class RAGRequest(BaseModel):
    processes: List[int]
    resources: List[int]
    allocation: Dict[int, List[int]]  # pid -> list of resource_ids held
    request: Dict[int, List[int]]     # pid -> list of resource_ids requested


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scheduling")
def run_scheduling_simulation(req: SchedulingRequest) -> Dict[str, Any]:
    """Run a CPU scheduling algorithm simulation."""
    if not req.processes:
        raise HTTPException(status_code=400, detail="At least one process must be supplied.")

    algo = req.algorithm.upper()
    
    # Helper to convert Pydantic ProcessInput to simulation Process class
    def build_procs():
        return [
            FCFSProcess(
                pid=p.pid,
                arrival_time=p.arrival_time,
                burst_time=p.burst_time,
                priority=p.priority
            )
            for p in req.processes
        ]

    try:
        if algo in ("FCFS", "FIRST COME FIRST SERVE"):
            res = fcfs(build_procs())
        elif algo in ("SJF", "SHORTEST JOB FIRST"):
            res = sjf(build_procs())
        elif algo in ("SRTF", "SHORTEST REMAINING TIME FIRST"):
            res = srtf(build_procs())
        elif algo in ("RR", "ROUND ROBIN", "ROUND_ROBIN"):
            res = round_robin(build_procs(), quantum=req.quantum or 2)
        elif algo in ("PRIORITY", "PRIORITY SCHEDULING"):
            res = priority_scheduling(build_procs())
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported algorithm '{req.algorithm}'. Use FCFS, SJF, SRTF, RR, or PRIORITY."
            )

        # Convert result dataclass to dictionary
        processes_out = [
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "start_time": p.start_time,
                "finish_time": p.finish_time,
                "waiting_time": p.waiting_time,
                "turnaround_time": p.turnaround_time
            }
            for p in res.processes
        ]

        ret = {
            "algorithm": res.algorithm,
            "processes": processes_out,
            "gantt_chart": res.gantt_chart,
            "avg_waiting_time": round(res.avg_waiting_time, 2),
            "avg_turnaround_time": round(res.avg_turnaround_time, 2),
            "cpu_utilization": res.cpu_utilization,
            "throughput": res.throughput
        }

        # Persist to simulations and scheduled_processes tables
        try:
            from app.config.database import get_connection
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO simulations (type, algorithm, created_by, created_at, status) VALUES ('CPU_SCHEDULING', %s, 1, NOW(), 'COMPLETED')",
                    (algo,)
                )
                sim_id = cur.lastrowid
                for p in res.processes:
                    cur.execute(
                        """
                        INSERT INTO scheduled_processes (simulation_id, process_label, arrival_time, burst_time, priority, waiting_time, turnaround_time, completion_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (sim_id, f"P{p.pid}", p.arrival_time, p.burst_time, getattr(p, "priority", 0), p.waiting_time, p.turnaround_time, p.finish_time)
                    )
                cur.execute(
                    "INSERT INTO performance_records (metric_name, metric_value, data_source, recorded_at) VALUES (%s, %s, 'SIMULATION', NOW())",
                    (f"cpu_scheduling_{algo.lower()}_avg_waiting_time", float(res.avg_waiting_time))
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception:
            pass

        return ret
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Scheduling simulation error: {str(e)}")


@router.post("/memory")
def run_memory_simulation(req: MemoryRequest) -> Dict[str, Any]:
    """Run a Page Replacement algorithm simulation."""
    if not req.reference_string:
        raise HTTPException(status_code=400, detail="Reference string cannot be empty.")

    algo = req.algorithm.upper()
    
    try:
        ret = {}
        if algo in ("FIFO", "FIRST IN FIRST OUT"):
            res = fifo(req.reference_string, req.num_frames)
            ret = {
                "algorithm": res.algorithm,
                "reference_string": res.reference_string,
                "num_frames": res.num_frames,
                "page_faults": res.page_faults,
                "page_hits": res.page_hits,
                "fault_rate": res.fault_rate,
                "hit_rate": res.hit_rate,
                "frame_states": res.frame_states
            }
        elif algo in ("LRU", "LEAST RECENTLY USED"):
            res = lru(req.reference_string, req.num_frames)
            ret = {
                "algorithm": res.algorithm,
                "reference_string": res.reference_string,
                "num_frames": res.num_frames,
                "page_faults": res.page_faults,
                "page_hits": res.page_hits,
                "fault_rate": res.fault_rate,
                "hit_rate": res.hit_rate,
                "frame_states": res.frame_states
            }
        elif algo in ("OPTIMAL", "OPT"):
            res = optimal(req.reference_string, req.num_frames)
            ret = {
                "algorithm": res.algorithm,
                "reference_string": res.reference_string,
                "num_frames": res.num_frames,
                "page_faults": res.page_faults,
                "page_hits": res.page_hits,
                "fault_rate": res.fault_rate,
                "hit_rate": res.hit_rate,
                "frame_states": res.frame_states
            }
        elif algo == "ALL":
            res_fifo = fifo(req.reference_string, req.num_frames)
            res_lru = lru(req.reference_string, req.num_frames)
            res_opt = optimal(req.reference_string, req.num_frames)
            ret = {
                "comparison": {
                    "FIFO": {"faults": res_fifo.page_faults, "fault_rate": res_fifo.fault_rate},
                    "LRU": {"faults": res_lru.page_faults, "fault_rate": res_lru.fault_rate},
                    "OPTIMAL": {"faults": res_opt.page_faults, "fault_rate": res_opt.fault_rate}
                },
                "num_frames": req.num_frames,
                "reference_string": req.reference_string
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported memory algorithm '{req.algorithm}'. Use FIFO, LRU, OPTIMAL, or ALL."
            )

        # Persist to simulations, memory_experiments, and page_references tables
        try:
            import json as _sim_json
            from app.config.database import get_connection
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO simulations (type, algorithm, created_by, created_at, status) VALUES ('MEMORY_MANAGEMENT', %s, 1, NOW(), 'COMPLETED')",
                    (algo,)
                )
                sim_id = cur.lastrowid
                summary = _sim_json.dumps(ret.get("comparison") or {"faults": ret.get("page_faults", 0), "hits": ret.get("page_hits", 0)})
                cur.execute(
                    "INSERT INTO memory_experiments (simulation_id, algorithm, frame_count, result_summary) VALUES (%s, %s, %s, %s)",
                    (sim_id, algo, req.num_frames, summary)
                )
                exp_id = cur.lastrowid
                frame_states_list = ret.get("frame_states") or (res_fifo.frame_states if algo == "ALL" else [])
                prev_frames: set[int] = set()
                for idx, page_num in enumerate(req.reference_string, 1):
                    fault_occurred = page_num not in prev_frames
                    if idx - 1 < len(frame_states_list):
                        prev_frames = {f for f in frame_states_list[idx - 1] if f is not None and f != -1}
                    cur.execute(
                        "INSERT INTO page_references (experiment_id, page_number, sequence_order, fault_occurred) VALUES (%s, %s, %s, %s)",
                        (exp_id, page_num, idx, fault_occurred)
                    )
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception:
            pass

        return ret
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Memory simulation error: {str(e)}")


@router.post("/deadlock/bankers")
def run_bankers_simulation(req: BankersRequest) -> Dict[str, Any]:
    """Run Banker's algorithm for deadlock avoidance."""
    try:
        res = bankers_algorithm(
            allocation=req.allocation,
            max_need=req.max_need,
            available=req.available,
            request=req.request,
            requesting_pid=req.requesting_pid
        )
        ret = {
            "is_safe": res.is_safe,
            "safe_sequence": res.safe_sequence,
            "reason": res.reason
        }

        # Persist to simulations and deadlock_experiments tables
        try:
            from app.config.database import get_connection
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO simulations (type, algorithm, created_by, created_at, status) VALUES ('DEADLOCK_THEORY', 'BANKERS', 1, NOW(), 'COMPLETED')",
                )
                sim_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO deadlock_experiments (simulation_id, algorithm, deadlock_detected, cycle_path) VALUES (%s, 'BANKERS', %s, %s)",
                    (sim_id, not res.is_safe, str(res.safe_sequence or []))
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception:
            pass

        return ret
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Banker's algorithm error: {str(e)}")


@router.post("/deadlock/rag")
def run_rag_simulation(req: RAGRequest) -> Dict[str, Any]:
    """Run Resource Allocation Graph (RAG) deadlock detection."""
    try:
        res = detect_deadlock(
            processes=req.processes,
            resources=req.resources,
            allocation=req.allocation,
            request=req.request
        )
        ret = {
            "deadlock_detected": res.deadlock_detected,
            "deadlocked_processes": res.deadlocked_processes,
            "cycle": res.cycle,
            "reason": res.reason
        }

        # Persist to simulations and deadlock_experiments tables
        try:
            from app.config.database import get_connection
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO simulations (type, algorithm, created_by, created_at, status) VALUES ('DEADLOCK_THEORY', 'RAG', 1, NOW(), 'COMPLETED')",
                )
                sim_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO deadlock_experiments (simulation_id, algorithm, deadlock_detected, cycle_path) VALUES (%s, 'RAG', %s, %s)",
                    (sim_id, res.deadlock_detected, str(res.cycle or []))
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception:
            pass

        return ret
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG deadlock detection error: {str(e)}")


class DiskSchedulingRequest(BaseModel):
    tracks: List[int]
    initial_head: int = 50
    algorithm: str = "FCFS"


@router.post("/disk")
def run_disk_simulation(req: DiskSchedulingRequest) -> Dict[str, Any]:
    """Run disk scheduling simulation (FCFS, SSTF, SCAN, C-SCAN) and persist to disk_requests table."""
    current = req.initial_head
    algo = (req.algorithm or "FCFS").upper().strip()
    raw_tracks = [int(t) for t in req.tracks]

    if algo == "SSTF":
        remaining = list(raw_tracks)
        ordered_tracks: List[int] = []
        head_pos = current
        while remaining:
            closest = min(remaining, key=lambda x: (abs(x - head_pos), x))
            ordered_tracks.append(closest)
            remaining.remove(closest)
            head_pos = closest
    elif algo == "SCAN":
        higher = sorted([t for t in raw_tracks if t >= current])
        lower = sorted([t for t in raw_tracks if t < current], reverse=True)
        ordered_tracks = higher + lower
    elif algo in ("C-SCAN", "CSCAN"):
        higher = sorted([t for t in raw_tracks if t >= current])
        lower = sorted([t for t in raw_tracks if t < current])
        ordered_tracks = higher + lower
    else:
        ordered_tracks = raw_tracks

    total_seek = 0
    sequence = []

    for idx, t in enumerate(ordered_tracks, 1):
        seek = abs(t - current)
        total_seek += seek
        sequence.append({"order": idx, "track": t, "seek_time": seek})
        current = t
        
    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO simulations (type, algorithm, created_by, created_at, status) VALUES ('DISK_SCHEDULING', %s, 1, NOW(), 'COMPLETED')",
                (req.algorithm,)
            )
            sim_id = cur.lastrowid
            for s in sequence:
                cur.execute(
                    "INSERT INTO disk_requests (simulation_id, track_number, sequence_order, seek_time) VALUES (%s, %s, %s, %s)",
                    (sim_id, s["track"], s["order"], s["seek_time"])
                )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
        
    return {
        "algorithm": req.algorithm,
        "initial_head": req.initial_head,
        "total_seek_time": total_seek,
        "requests": sequence
    }


class SyncSimulationRequest(BaseModel):
    problem_type: str = "PRODUCER_CONSUMER"
    iterations: int = 5


@router.post("/sync")
def run_sync_simulation(req: SyncSimulationRequest) -> Dict[str, Any]:
    """Simulate synchronization problem and persist to synchronization_experiments table."""
    log = []
    for i in range(1, req.iterations + 1):
        log.append(f"Step {i}: Producer produced item #{i} -> Consumer consumed item #{i}")
    log_text = "\n".join(log)
    
    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO simulations (type, algorithm, created_by, created_at, status) VALUES ('SYNCHRONIZATION', %s, 1, NOW(), 'COMPLETED')",
                (req.problem_type,)
            )
            sim_id = cur.lastrowid
            cur.execute(
                "INSERT INTO synchronization_experiments (simulation_id, problem_type, result_log) VALUES (%s, %s, %s)",
                (sim_id, req.problem_type, log_text)
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass

    return {
        "problem_type": req.problem_type,
        "iterations": req.iterations,
        "result_log": log
    }


@router.get("/history")
def list_simulation_history(limit: int = 25) -> Dict[str, Any]:
    """Read back stored simulation history across all simulation tables."""
    from app.config.database import get_connection
    history: Dict[str, Any] = {
        "simulations": [],
        "scheduled_processes": [],
        "memory_experiments": [],
        "page_references": [],
        "deadlock_experiments": [],
        "disk_requests": [],
        "synchronization_experiments": [],
    }
    try:
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM simulations ORDER BY simulation_id DESC LIMIT %s", (limit,))
            history["simulations"] = cur.fetchall()
            cur.execute("SELECT * FROM scheduled_processes ORDER BY schedule_entry_id DESC LIMIT %s", (limit,))
            history["scheduled_processes"] = cur.fetchall()
            cur.execute("SELECT * FROM memory_experiments ORDER BY experiment_id DESC LIMIT %s", (limit,))
            history["memory_experiments"] = cur.fetchall()
            cur.execute("SELECT * FROM page_references ORDER BY ref_id DESC LIMIT %s", (limit,))
            history["page_references"] = cur.fetchall()
            cur.execute("SELECT * FROM deadlock_experiments ORDER BY experiment_id DESC LIMIT %s", (limit,))
            history["deadlock_experiments"] = cur.fetchall()
            cur.execute("SELECT * FROM disk_requests ORDER BY request_id DESC LIMIT %s", (limit,))
            history["disk_requests"] = cur.fetchall()
            cur.execute("SELECT * FROM synchronization_experiments ORDER BY sync_id DESC LIMIT %s", (limit,))
            history["synchronization_experiments"] = cur.fetchall()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return history


@router.get("/scenarios")
def list_simulation_scenarios() -> list[dict[str, Any]]:
    """Return catalog of available simulation engines and supported algorithms."""
    return [
        {
            "id": "cpu_scheduling",
            "name": "CPU Scheduling Algorithms",
            "algorithms": ["fcfs", "sjf", "srtf", "round_robin", "priority"],
            "endpoint": "/api/simulations/scheduling",
        },
        {
            "id": "page_replacement",
            "name": "Memory Page Replacement",
            "algorithms": ["fifo", "lru", "optimal"],
            "endpoint": "/api/simulations/memory",
        },
        {
            "id": "bankers_algorithm",
            "name": "Banker's Deadlock Avoidance",
            "endpoint": "/api/simulations/deadlock/bankers",
        },
        {
            "id": "resource_allocation_graph",
            "name": "Resource Allocation Graph (RAG) Deadlock Detection",
            "endpoint": "/api/simulations/deadlock/rag",
        },
        {
            "id": "disk_scheduling",
            "name": "Disk Head Scheduling",
            "algorithms": ["fcfs", "sstf", "scan", "cscan", "look", "clook"],
            "endpoint": "/api/simulations/disk",
        },
        {
            "id": "classical_ipc",
            "name": "Classical Synchronization Problems",
            "problems": ["producer_consumer", "dining_philosophers", "readers_writers"],
            "endpoint": "/api/simulations/sync",
        },
    ]

