# OS-DBX Backend

FastAPI backend for OS-DBX. The backend now exposes the DBMS foundation,
cross-layer correlation, deadlock analysis, recovery experiments, and DBMS
schedule analysis. The React frontend and core OS collectors remain separate
team-owned components.

## Core endpoints

```
GET  /health
POST /api/events
POST /api/transactions/begin
POST /api/transactions/{id}/read|write|commit|rollback
POST /api/locks
POST /api/query-executions
POST /api/correlations
POST /api/correlations/auto
POST /api/deadlocks/detect
POST /api/deadlocks/detect/live
GET  /api/deadlocks/incidents?limit=50
POST /api/dbms-events/collect
GET  /api/dbms-events/observations?limit=50
POST /api/performance/records
GET  /api/performance/records?limit=50&trace_id=1
GET  /api/incidents/{id}/investigation
POST /api/incidents/{id}/replay
POST /api/recovery/recover
POST /api/schedules/analyze
POST /api/what-if/schedules
POST /api/what-if/recovery
GET  /api/what-if/scenarios?limit=50
GET  /api/what-if/scenarios/{id}
```

Set `EVENT_STORAGE=mysql` to persist OS events in the `os_events` table. The
default `memory` mode keeps local API tests independent of a running MySQL
server.

`POST /api/dbms-events/collect` polls MySQL Performance Schema for completed
statements and stores normalized observations in `dbms_query_observations`.
The collector uses MySQL thread/event IDs for deduplication. It leaves OS PID
and application transaction mapping for the correlation layer because MySQL
does not provide that mapping reliably.
Collector and repository SQL statements are excluded from the observations so
the collector cannot record its own polling or persistence work. The
collector's MySQL connection is excluded as well, including its periodic
`COMMIT` statements.

Each newly persisted DBMS observation also creates two global performance
records: `dbms.query.execution_time_ms` and `dbms.query.rows_affected`. Trace
specific metrics can be added through `POST /api/performance/records`.

`POST /api/correlations/auto` accepts a DBMS observation ID and a timestamp
window. It matches the observation to a recorded query by exact query type and
text within that window. Automatic correlation proceeds only when exactly one
query execution matches; zero matches or multiple matches return a reason and
do not create a trace. Nearby OS events must also match the query's PID. Time
limits candidate selection but does not establish identity by itself.

### Cross-layer identity contract

The application that owns the OS process is the authority for its OS PID and
application transaction ID. It starts a transaction with
`POST /api/transactions/begin` using that PID, then uses the returned
`transaction_id` for its query execution and lock requests. The query execution
request carries both `pid` and `transaction_id`; the backend assigns its
`query_id`. Locks are associated to that transaction, so the stable chain is:

```text
application OS PID -> application transaction_id -> backend query_id
                                      |                 |
                                      +-> lock_id       +-> DBMS observation
```

MySQL `THREAD_ID` and `CONNECTION_ID` are source identifiers only. They are not
treated as an OS PID or application transaction ID. To attach a Performance
Schema observation to an application query, OS-DBX requires an exact query
type/text match within the configured time window and exactly one candidate.
Ambiguous matches are rejected. Correlation event IDs are unique within a
correlation request, all candidate events must agree on PID, transaction ID,
and query ID, and event ordering is timestamp then OS event ID (so equal
timestamps have a stable order). This is deterministic association evidence;
timestamps alone never prove identity.

The legacy `confidence_score` response/database field remains nullable for
compatibility and is returned as `null`. OS-DBX does not calculate a
probability score.

Incident investigation returns a timeline assembled from the incident, trace,
OS events, query executions, transaction operations, locks, and trace metrics.
Incident replay saves a deterministic replay of that timeline and never
executes captured SQL against the database. Replay returns HTTP 409 when the
incident has no linked trace or its trace has no correlated event rows; it
does not persist an empty replay.

The what-if endpoints run the existing schedule serializability and recovery
engines, save both the input and result, and make scenarios queryable.

The MySQL Performance Schema must be enabled, and the long statement-history
consumer must be enabled before collection. Check it with:

```sql
SELECT NAME, ENABLED
FROM performance_schema.setup_consumers
WHERE NAME LIKE 'events_statements%';
```

If `events_statements_history_long` is `NO`, enable it as a MySQL administrator:

```sql
UPDATE performance_schema.setup_consumers
SET ENABLED = 'YES'
WHERE NAME = 'events_statements_history_long';
```

This is a runtime setting and may need to be repeated after a MySQL restart, or
configured through the MySQL Performance Schema startup options for a durable
installation.

For continuous collection, start a second backend terminal and run:

```powershell
cd backend
venv\Scripts\activate
python -m app.collectors.dbms_collector_worker
```

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
- `GET  http://localhost:8000/health/details` -> service and correlation
  readiness details
- `GET  http://localhost:8000/docs` -> interactive Swagger UI
- `GET  http://localhost:8000/api/demo/correlation` -> self-contained
  correlation proof with a PASS/FAIL result; this endpoint does not require
  MySQL and is suitable for a teammate or professor demonstration
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

## Remaining integration work

- OS collector-to-API wiring and end-to-end PID-to-transaction propagation
- Frontend screens and visualizations (there is no frontend source in this checkout)
- Incident/deadlock trace linking and a verified database-backed demo replay
- Production deployment, authentication, retention policies, and durable
  Performance Schema startup configuration
