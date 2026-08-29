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
