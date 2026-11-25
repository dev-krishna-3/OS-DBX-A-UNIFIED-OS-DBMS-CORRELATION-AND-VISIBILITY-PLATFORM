"""
OS-DBX - OS Event Collector (Person 1 module)

Polls the live process table and emits OS events in the shared JSON
contract agreed with the DBMS side:

    {
        "timestamp": "...",
        "pid": ...,
        "ppid": ...,
        "user": "...",
        "event_type": "process_created" | "process_terminated",
        "file_path": "..." (executable path, if available),
        "state": "..." (e.g. "running", "sleeping", "zombie")
    }

Note on "state" for process_terminated events: this reflects the
process's last observed status before it disappeared from the process
table, not a literal "terminated" status - psutil has no way to
inspect a process that no longer exists.

This runs standalone for now - no FastAPI or MySQL dependency - so it
can be built and tested independently. Later, `emit_event()` can be
swapped to POST to the backend's /api/events endpoint instead of
printing/writing to a file.
"""

import json
import time
import psutil
from datetime import datetime, timezone
from pathlib import Path

POLL_INTERVAL_SECONDS = 2
EVENTS_LOG_FILE = Path(__file__).parent / "events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot_processes() -> dict:
    """Return {pid: process_info_dict} for all currently running processes."""
    snapshot = {}
    for proc in psutil.process_iter(["pid", "ppid", "name", "username", "exe", "status"]):
        try:
            info = proc.info
            snapshot[info["pid"]] = {
                "ppid": info.get("ppid"),
                "name": info.get("name"),
                "user": info.get("username"),
                "file_path": info.get("exe") or None,
                "state": info.get("status"),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process may have exited mid-scan, or we lack permission to inspect it.
            continue
    return snapshot


def build_event(pid: int, info: dict, event_type: str) -> dict:
    return {
        "timestamp": now_iso(),
        "pid": pid,
        "ppid": info.get("ppid"),
        "user": info.get("user"),
        "event_type": event_type,
        "file_path": info.get("file_path"),
        "state": info.get("state"),
    }


def emit_event(event: dict) -> None:
    """Where events go. For now: print + append to a local JSONL file.
    Later: replace/extend this to POST to the FastAPI backend."""
    print(json.dumps(event))
    with open(EVENTS_LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")


def diff_snapshots(previous: dict, current: dict) -> list:
    """Compare two process snapshots and return the OS events between them."""
    events = []

    created_pids = current.keys() - previous.keys()
    terminated_pids = previous.keys() - current.keys()

    for pid in created_pids:
        events.append(build_event(pid, current[pid], "process_created"))

    for pid in terminated_pids:
        events.append(build_event(pid, previous[pid], "process_terminated"))

    return events


def run(poll_interval: int = POLL_INTERVAL_SECONDS):
    print(f"[os-monitor] starting, polling every {poll_interval}s. "
          f"Writing events to {EVENTS_LOG_FILE}")
    previous = snapshot_processes()

    try:
        while True:
            time.sleep(poll_interval)
            current = snapshot_processes()
            events = diff_snapshots(previous, current)
            for event in events:
                emit_event(event)
            previous = current
    except KeyboardInterrupt:
        print("\n[os-monitor] stopped.")


if __name__ == "__main__":
    run()
