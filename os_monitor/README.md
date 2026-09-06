# OS Event Collector (Person 1)

Standalone process-monitoring script. No backend or database dependency yet -
runs on its own so it can be built and tested independently.

## Run it

```
cd os_monitor
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python collector.py
```

It polls the process table every 2 seconds, detects new and terminated
processes, and:
- prints each event as a JSON line to the console
- appends each event to `events.jsonl` in this folder

## Event shape (matches the team's agreed OS-event contract)

```json
{
  "timestamp": "2026-08-26T10:15:03.221+00:00",
  "pid": 4211,
  "ppid": 1,
  "user": "krishna",
  "event_type": "process_created",
  "file_path": "/usr/bin/python3",
  "state": "running"
}
```

## Try it

Open a second terminal and run something simple, e.g. `sleep 5` or open
a text editor - you should see a `process_created` event appear, then a
`process_terminated` event once it exits.

## Next steps (once this works)

1. Add filesystem event monitoring (watchdog library) for file
   create/modify/delete events, matching the FILESYSTEM section of the
   master doc.
2. Add CPU/memory resource metrics per process.
3. Replace `emit_event()`'s print/file-write with a POST request to the
   backend's `/api/events` endpoint (once Person 4 has that route ready),
   so events flow into MySQL instead of a local file.


## Filesystem Event Collector (filesystem_monitor.py)

Watches a directory recursively for file create/modify/delete/rename
events using the watchdog library, emitting them in the same os_events
shape as collector.py.

### Setup

Add to requirements.txt: `watchdog==6.0.0`, then `pip install -r requirements.txt`.

### Run it

```
python filesystem_monitor.py
```

With no argument, it watches a `watched_folder` directory created next
to the script (deliberately NOT your whole filesystem, which would be
extremely noisy and slow). To watch different folder(s) instead, pass
one or more paths as separate arguments:

```
python filesystem_monitor.py "C:\path\to\folder1" "C:\path\to\folder2"
```

All events from every watched path land in the same
filesystem_events.jsonl, using one shared log - the `file_path` field
in each event tells you which location it actually came from, so you
can watch multiple relevant locations at once (e.g. your test app's
working directory AND wherever MySQL's data lives) without needing
separate script instances.

Writes to `filesystem_events.jsonl` in this folder, same pattern as
the other collectors.

### Event shape

```json
{
  "timestamp": "2026-09-02T03:14:18.381676+00:00",
  "pid": null,
  "event_type": "file_created",
  "file_path": "watched_folder/test1.txt",
  "details": "{\"is_directory\": false}"
}
```

For file_moved events, `details` also includes `old_path`.

### Notes

- `pid` is always null here by design, not a bug. Watchdog reports
  WHAT changed on disk, not WHICH process changed it - identifying the
  responsible process requires OS-level auditing (e.g. Linux auditd,
  or eBPF), which the master doc explicitly calls out as an
  advanced/future feature, not required for MVP.
- A single logical file write can sometimes produce two
  file_modified events in quick succession (e.g. once for the initial
  write, once when the file handle closes) - this is normal OS/watchdog
  behavior, not a duplicate-event bug.
- Directory-level "modified" events are filtered out - only actual
  file content changes are logged, since directories fire spurious
  modified events whenever a file inside them changes.

### Try it

Run the script, then in the watched folder: create a text file, edit
it, rename it, and delete it. Watch filesystem_events.jsonl fill up
with each step.