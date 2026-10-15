"""Saved what-if schedule and recovery analysis APIs."""

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.database import get_connection
from app.models.recovery import RecoveryResult
from app.models.schedules import ScheduleAnalysisResult
from app.models.what_if import (
    WhatIfOSRequest,
    WhatIfRecoveryRequest,
    WhatIfScenario,
    WhatIfScheduleRequest,
)
from app.repositories.what_if_repository import WhatIfRepository
from app.services.recovery_service import RecoveryService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/what-if", tags=["what-if"])


def get_what_if_repository(connection=Depends(get_connection)):
    try:
        yield WhatIfRepository(connection)
    finally:
        connection.close()


@router.post("/schedules", response_model=WhatIfScenario, status_code=201)
def analyze_schedule_what_if(
    request: WhatIfScheduleRequest,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    result = ScheduleService().analyze(request.operations)
    return repository.create(
        "SCHEDULE",
        request.name,
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
    )


@router.post("/recovery", response_model=WhatIfScenario, status_code=201)
def analyze_recovery_what_if(
    request: WhatIfRecoveryRequest,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    result = RecoveryService().recover(request.initial_state, request.logs)
    return repository.create(
        "RECOVERY",
        request.name,
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
    )


@router.post("/os", response_model=WhatIfScenario, status_code=201)
def analyze_os_what_if(
    request: WhatIfOSRequest,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    """Analyze deterministic hypothetical OS scenario (load, memory, disk, contention)."""
    params = request.parameters
    scenario_type = request.scenario_type
    
    if scenario_type == "CPU_LOAD":
        pcount = int(params.get("process_count", 10))
        burst_ms = float(params.get("avg_burst_ms", 50.0))
        cores = int(params.get("core_count", 4))
        total_demand = pcount * burst_ms
        utilization = min(100.0, (total_demand / (cores * 1000.0)) * 100.0)
        wait_ms = max(0.0, (pcount - cores) * (burst_ms / max(1, cores)))
        result = {
            "mode": "[ANALYSIS] [SIMULATION]",
            "scenario": "CPU & Process Load Scaling",
            "process_count": pcount,
            "core_count": cores,
            "estimated_cpu_utilization_pct": round(utilization, 2),
            "estimated_avg_wait_ms": round(wait_ms, 2),
            "throughput_procs_per_sec": round((1000.0 / max(1.0, burst_ms)) * cores, 2),
            "bottleneck_risk": "HIGH" if utilization > 85.0 else ("MODERATE" if utilization > 60.0 else "LOW"),
            "recommendation": "Scale CPU cores or apply CFS nice-level throttling" if utilization > 85.0 else "Operating within safe capacity bounds"
        }
    elif scenario_type == "MEMORY_PRESSURE":
        alloc_mb = float(params.get("allocated_mb", 7500))
        total_mb = float(params.get("total_ram_mb", 8192))
        frames = int(params.get("frames", 3))
        ref_string = params.get("page_references", [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5])
        
        # Deterministic FIFO simulation
        memory_usage_pct = (alloc_mb / max(1.0, total_mb)) * 100.0
        fifo_frames = []
        faults = 0
        for p in ref_string:
            if p not in fifo_frames:
                faults += 1
                if len(fifo_frames) < frames:
                    fifo_frames.append(p)
                else:
                    fifo_frames.pop(0)
                    fifo_frames.append(p)
        fault_rate = faults / max(1, len(ref_string))
        result = {
            "mode": "[ANALYSIS] [SIMULATION]",
            "scenario": "Virtual Memory Pressure & Page Replacement",
            "allocated_mb": alloc_mb,
            "total_ram_mb": total_mb,
            "memory_usage_pct": round(memory_usage_pct, 2),
            "page_reference_count": len(ref_string),
            "page_faults": faults,
            "page_fault_rate": round(fault_rate, 3),
            "thrashing_risk": "CRITICAL" if memory_usage_pct > 90.0 or fault_rate > 0.6 else "STABLE",
            "recommendation": "Increase OS swapfile size or expand RAM" if memory_usage_pct > 90.0 else "Memory allocation within safe margins"
        }
    elif scenario_type == "DISK_IO":
        requests = params.get("requests", [98, 183, 37, 122, 14, 124, 65, 67])
        head = int(params.get("current_head", 53))
        algo = str(params.get("algorithm", "SSTF")).upper()
        
        # Deterministic SSTF seek calculation
        pending = list(requests)
        cur = head
        total_seek = 0
        sequence = []
        while pending:
            nearest = min(pending, key=lambda x: abs(x - cur))
            total_seek += abs(nearest - cur)
            cur = nearest
            sequence.append(cur)
            pending.remove(nearest)
            
        result = {
            "mode": "[ANALYSIS] [SIMULATION]",
            "scenario": "Disk Head Scheduling & I/O Contention",
            "initial_head": head,
            "request_count": len(requests),
            "algorithm": algo,
            "execution_sequence": sequence,
            "total_head_movement_cylinders": total_seek,
            "avg_seek_time_ms": round(total_seek * 0.12, 2),
            "io_saturation_risk": "HIGH" if total_seek > 500 else "LOW"
        }
    else: # RESOURCE_CONTENTION / SCHEDULING_POLICY / PROCESS_LIFECYCLE
        tasks = int(params.get("concurrent_tasks", 8))
        shared = int(params.get("shared_locks", 2))
        contention_index = round(min(1.0, (tasks * shared) / 20.0), 2)
        result = {
            "mode": "[ANALYSIS] [SIMULATION]",
            "scenario": "OS Concurrency & Resource Contention",
            "concurrent_tasks": tasks,
            "shared_resources": shared,
            "contention_index": contention_index,
            "lock_convoy_probability": f"{int(contention_index * 100)}%",
            "deadlock_risk": "ELEVATED" if contention_index > 0.6 else "MINIMAL",
            "recommendation": "Adopt hierarchical lock ordering to prevent deadlock cycles" if contention_index > 0.6 else "Acceptable concurrency load"
        }
        
    return repository.create(
        scenario_type,
        request.name,
        request.model_dump(mode="json"),
        result,
    )


@router.get("/scenarios", response_model=list[WhatIfScenario])
def list_what_if_scenarios(
    limit: int = Query(default=50, ge=1, le=500),
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> list[WhatIfScenario]:
    try:
        return repository.recent(limit)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/scenarios/{scenario_id}", response_model=WhatIfScenario)
def get_what_if_scenario(
    scenario_id: int,
    repository: WhatIfRepository = Depends(get_what_if_repository),
) -> WhatIfScenario:
    try:
        scenario = repository.get(scenario_id)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if scenario is None:
        raise HTTPException(status_code=404, detail="What-if scenario not found")
    return scenario
