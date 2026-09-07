# OS-DBX Backend

FastAPI backend for OS-DBX. This document covers **Milestone 1: backend
foundation + event ingestion API** only.

## Scope of this milestone

```
POST /api/events
        |
   Pydantic validation
        |
   Event service
        |
   temporary in-memory storage
        |
GET /api/events
```

No MySQL connection, no correlation engine, no simulations yet - those
are later milestones (see project context doc).

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --app-dir .
```

Then:
- `GET  http://localhost:8000/health` -> `{"status": "ok"}`
- `POST http://localhost:8000/api/events` with an OS event body
- `GET  http://localhost:8000/api/events?limit=50`

## Event contract

Matches `os_monitor/collector.py` exactly:

```json
{
  "timestamp": "2026-08-26T10:15:03.221+00:00",
  "pid": 4211,
  "ppid": 1,
  "user": "krishna",
  "event_type": "process_created",
  "file_path": "/usr/bin/python3"
}
```

- `event_type` is currently restricted to `process_created` and
  `process_terminated` - the two types the collector emits.
- `file_path` may be `null`.
- `pid` must be a positive integer; `ppid` may be `0` (e.g. init).

## Tests

```bash
cd backend
pytest
```

## What's intentionally NOT here yet

- MySQL connection / persistence (`app/repositories/event_repository.py`
  is a placeholder - Milestone 2)
- The OS collector still writes to `events.jsonl` locally; wiring it to
  POST here is Milestone 3
- Correlation engine (Milestone 6)
- Any frontend code (owned by the frontend teammate)
