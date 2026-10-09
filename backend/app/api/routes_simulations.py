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

        return {
            "algorithm": res.algorithm,
            "processes": processes_out,
            "gantt_chart": res.gantt_chart,
            "avg_waiting_time": round(res.avg_waiting_time, 2),
            "avg_turnaround_time": round(res.avg_turnaround_time, 2),
            "cpu_utilization": res.cpu_utilization,
            "throughput": res.throughput
        }
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
        if algo in ("FIFO", "FIRST IN FIRST OUT"):
            res = fifo(req.reference_string, req.num_frames)
            return {
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
            return {
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
            return {
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
            return {
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
        return {
            "is_safe": res.is_safe,
            "safe_sequence": res.safe_sequence,
            "reason": res.reason
        }
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
        return {
            "deadlock_detected": res.deadlock_detected,
            "deadlocked_processes": res.deadlocked_processes,
            "cycle": res.cycle,
            "reason": res.reason
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG deadlock detection error: {str(e)}")
