"""
OS-DBX - Filesystem Event Collector (Person 1 module)

Watches a directory (recursively) for file create/modify/delete/rename
events using the watchdog library, and emits them in the same
os_events shape used by collector.py:

    {
        "timestamp": "...",
        "pid": null,
        "event_type": "file_created" | "file_modified" | "file_deleted" | "file_moved",
        "file_path": "...",
        "details": "{...json...}"
    }

Note on pid: watchdog reports WHAT changed on disk, not WHICH process
did it - that requires OS-level auditing (e.g. Linux auditd or eBPF),
explicitly called out as an advanced/future feature in the master doc,
not required for MVP. pid is null here by design, not a bug.

Standalone for now, same pattern as collector.py and resource_monitor.py.
Later, emit_event() can be swapped to POST to the backend instead.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

EVENTS_LOG_FILE = Path(__file__).parent / "filesystem_events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_event(event: dict) -> None:
    print(json.dumps(event))
    with open(EVENTS_LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")


class OSDBXFileHandler(FileSystemEventHandler):
    """Translates watchdog's raw filesystem events into the shared
    os_events JSON contract."""

    def _build_event(self, event_type: str, file_path: str, details: dict = None) -> dict:
        return {
            "timestamp": now_iso(),
            "pid": None,
            "event_type": event_type,
            "file_path": file_path,
            "details": json.dumps(details or {}),
        }

    def on_created(self, event):
        emit_event(self._build_event(
            "file_created", event.src_path, {"is_directory": event.is_directory}
        ))

    def on_modified(self, event):
        # Directory "modified" events fire constantly as a side effect of
        # files changing inside them - only log actual file modifications.
        if event.is_directory:
            return
        emit_event(self._build_event(
            "file_modified", event.src_path, {"is_directory": False}
        ))

    def on_deleted(self, event):
        emit_event(self._build_event(
            "file_deleted", event.src_path, {"is_directory": event.is_directory}
        ))

    def on_moved(self, event):
        emit_event(self._build_event(
            "file_moved", event.dest_path,
            {"is_directory": event.is_directory, "old_path": event.src_path}
        ))


def run(watch_paths: List[str]):
    resolved_paths = []
    for wp in watch_paths:
        path = Path(wp).resolve()
        if not path.exists():
            print(f"[fs-monitor] path does not exist, skipping: {path}")
            continue
        resolved_paths.append(path)

    if not resolved_paths:
        print("[fs-monitor] no valid paths to watch - exiting.")
        sys.exit(1)

    print(f"[fs-monitor] watching {len(resolved_paths)} path(s) (recursively). "
          f"Writing events to {EVENTS_LOG_FILE}")
    for p in resolved_paths:
        print(f"  - {p}")

    handler = OSDBXFileHandler()
    observer = Observer()
    for path in resolved_paths:
        # One shared handler/log file across all watched paths - an event
        # from ANY of them lands in the same filesystem_events.jsonl, and
        # file_path in each event tells you which location it came from.
        observer.schedule(handler, str(path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[fs-monitor] stopped.")
    observer.join()


if __name__ == "__main__":
    # Default to a local "watched_folder" next to this script if no paths
    # are given - deliberately NOT the whole filesystem, which would be
    # extremely noisy and slow to test against.
    default_path = Path(__file__).parent / "watched_folder"
    default_path.mkdir(exist_ok=True)

    # Accept one or more paths as separate arguments, e.g.:
    #   python filesystem_monitor.py "C:\app\data" "C:\ProgramData\MySQL\data"
    watch_targets = sys.argv[1:] if len(sys.argv) > 1 else [str(default_path)]
    run(watch_targets)