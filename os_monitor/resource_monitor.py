"""
OS-DBX - Resource Metrics Collector (Person 1 module)

Polls per-process CPU, memory, and disk I/O usage, matching the
resource_metrics table's exact column names in the DBMS schema:

    {
        "timestamp": "...",
        "pid": ...,
        "cpu_usage": ...,      (percent)
        "memory_usage": ...,   (percent)
        "disk_io": ...,        (total read+write bytes since last poll)
        "network_io": null     (see note below)
    }

Standalone for now, same pattern as collector.py - prints events and
appends to resource_metrics.jsonl. Later, emit_metric() can be swapped
to POST to the backend instead.

Note on network_io: psutil does not expose per-process network traffic
in bytes on most platforms (only system-wide counters or a process's
open connection count). This field is left null for now - flagged to
the team as a scope question rather than silently faked.
"""

import json
import time
import psutil
from datetime import datetime, timezone
from pathlib import Path

POLL_INTERVAL_SECONDS = 5
METRICS_LOG_FILE = Path(__file__).parent / "resource_metrics.jsonl"

# Minimum CPU% or memory% to bother logging - avoids flooding the file
# with hundreds of near-zero entries for idle background processes.
CPU_THRESHOLD = 1.0
MEMORY_THRESHOLD = 0.5


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_metrics() -> list:
    """One pass over all processes, returning metric dicts for anything
    above the activity thresholds."""
    metrics = []

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pid = proc.info["pid"]

            # PID 0 is the "System Idle Process" on Windows (and similar
            # kernel bookkeeping entries on other platforms) - it isn't a
            # real workload, and its cpu_percent() reflects idle time
            # summed across all CPU cores, so it can read as several
            # hundred percent. Not a real process worth logging here.
            if pid == 0:
                continue

            # cpu_percent() needs a prior call to "warm up" per-process;
            # since process_iter already cached one, this call returns
            # usage since the last time psutil checked this process.
            cpu = proc.cpu_percent(interval=None)
            mem = proc.memory_percent()

            if cpu < CPU_THRESHOLD and mem < MEMORY_THRESHOLD:
                continue

            disk_read = None
            disk_write = None
            try:
                io = proc.io_counters()
                disk_read = io.read_bytes
                disk_write = io.write_bytes
            except (psutil.AccessDenied, NotImplementedError, AttributeError):
                # io_counters() needs elevated permission on some systems,
                # and isn't implemented on macOS at all.
                pass

            # Combine read+write into the single disk_io column the schema
            # expects. If both are unavailable, leave disk_io null rather
            # than reporting a misleading 0.
            if disk_read is None and disk_write is None:
                disk_io = None
            else:
                disk_io = (disk_read or 0) + (disk_write or 0)

            metrics.append({
                "timestamp": now_iso(),
                "pid": pid,
                "name": proc.info.get("name"),
                "cpu_usage": round(cpu, 2),
                "memory_usage": round(mem, 2),
                "disk_io": disk_io,
                "network_io": None,  # not feasible with plain psutil - see module docstring
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return metrics


def emit_metric(metric: dict) -> None:
    print(json.dumps(metric))
    with open(METRICS_LOG_FILE, "a") as f:
        f.write(json.dumps(metric) + "\n")


def run(poll_interval: int = POLL_INTERVAL_SECONDS):
    print(f"[resource-monitor] starting, polling every {poll_interval}s. "
          f"Writing metrics to {METRICS_LOG_FILE}")

    # Prime cpu_percent() for all processes - first call always returns 0.0
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    try:
        while True:
            time.sleep(poll_interval)
            for metric in collect_metrics():
                emit_metric(metric)
    except KeyboardInterrupt:
        print("\n[resource-monitor] stopped.")


if __name__ == "__main__":
    run()
