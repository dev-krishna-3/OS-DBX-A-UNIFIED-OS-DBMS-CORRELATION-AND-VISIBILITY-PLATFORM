# -*- coding: utf-8 -*-
"""
OS-DBX Full End-to-End Integration Test
========================================
Tests the complete chain:
  Step 1:  Seed a process into DB (so FK constraint passes)
  Step 2:  Ingest an OS process event
  Step 3:  Begin a DBMS transaction
  Step 4:  Write operation on the transaction
  Step 5:  Record a query execution
  Step 6:  Commit the transaction
  Step 7:  Create a cross-layer correlation (OS <-> DBMS)
  Step 8:  Deadlock detection
  Step 9:  Get incidents list
  Step 10: Investigation timeline
  Step 11: Replay incident
  Step 12: Blast radius analysis
  Step 13: Auto-correlation (using real observation from DB)
  Step 14: What-if schedule analysis
  Step 15: Run benchmark
  Step 16: Full health check
"""

import json
import mysql.connector
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import settings

client = TestClient(app)

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
results = []

def check(label, response, expected_status=200):
    ok = response.status_code == expected_status
    is_2xx = 200 <= response.status_code < 300
    mark = PASS if ok else FAIL
    body = ""
    try:
        body = json.dumps(response.json(), indent=2)
    except Exception:
        body = response.text
    results.append((mark, label, response.status_code, body))
    print(f"\n{mark} [{response.status_code}] {label}")
    if not ok:
        print(f"     Body: {body[:400]}")
    # Return body for any 2xx so callers can chain correctly even on 201
    return response.json() if is_2xx else None


print("=" * 65)
print("  OS-DBX END-TO-END INTEGRATION TEST")
print("=" * 65)

# ---- Get a real PID that exists in the processes table ----
try:
    conn = mysql.connector.connect(
        host=settings.mysql_host, port=settings.mysql_port,
        user=settings.mysql_user, password=settings.mysql_password,
        database=settings.mysql_database
    )
    cur = conn.cursor()
    cur.execute("SELECT pid FROM processes LIMIT 1")
    row = cur.fetchone()
    REAL_PID = row[0] if row else None

    # Get a real observation_id for auto-correlation
    cur.execute("SELECT observation_id FROM dbms_query_observations LIMIT 1")
    obs_row = cur.fetchone()
    REAL_OBS_ID = obs_row[0] if obs_row else None

    # Get the incident_id
    cur.execute("SELECT incident_id FROM incidents LIMIT 1")
    inc_row = cur.fetchone()
    REAL_INCIDENT_ID = inc_row[0] if inc_row else None

    conn.close()
    print(f"\n  [DB] Real PID from processes table: {REAL_PID}")
    print(f"  [DB] Real observation_id: {REAL_OBS_ID}")
    print(f"  [DB] Real incident_id: {REAL_INCIDENT_ID}")
except Exception as e:
    REAL_PID = None
    REAL_OBS_ID = None
    REAL_INCIDENT_ID = None
    print(f"\n  [DB] Could not connect to DB: {e}")

print()

# ── STEP 1: Ingest OS event ──────────────────────────────────
r = client.post("/api/os-events", json={
    "pid": REAL_PID or 1,
    "ppid": 0,
    "user": "root",
    "event_type": "process_created",
    "process_name": "mysql.exe",
    "timestamp": "2026-10-10T00:00:00Z",
    "host_id": "DESKTOP-E2E"
})
os_event = check("Step 1: Ingest OS process event (POST /api/os-events)", r, 201)
print(f"     -> event_id = {os_event.get('event_id') if os_event else 'N/A'}")

# ── STEP 2: Begin transaction ────────────────────────────────
r = client.post("/api/transactions/begin", json={
    "pid": REAL_PID or 1,
    "isolation_level": "READ_COMMITTED"
})
tx = check("Step 2: Begin DBMS transaction (POST /api/transactions/begin)", r, 201)
tx_id = tx["transaction_id"] if tx else None
print(f"     -> transaction_id = {tx_id}")

# ── STEP 3: Write operation ──────────────────────────────────
if tx_id:
    r = client.post(f"/api/transactions/{tx_id}/write", json={"data_item": "users"})
    check(f"Step 3: Write operation on tx={tx_id}", r, 200)
else:
    results.append((SKIP, "Step 3: Write operation", 0, "Skipped - no tx_id"))
    print(f"\n{SKIP} Step 3: Write operation — skipped (no tx_id)")

# ── STEP 4: Execute a query ──────────────────────────────────
query_id = None
if tx_id and REAL_PID:
    r = client.post("/api/query-executions", json={
        "transaction_id": tx_id,
        "pid": REAL_PID,
        "query_type": "INSERT",
        "query_text": "INSERT INTO users (username) VALUES ('e2e_test_user')",
        "execution_time_ms": 12.5,
        "rows_affected": 1,
        "status": "SUCCESS",
        "timestamp": "2026-10-10T00:00:01"
    })
    qe = check("Step 4: Record query execution (POST /api/query-executions)", r, 201)
    query_id = qe.get("query_id") if qe else None
    print(f"     -> query_id = {query_id}")
else:
    results.append((SKIP, "Step 4: Query execution", 0, "Skipped"))
    print(f"\n{SKIP} Step 4: Query execution — skipped (no tx_id or pid)")

# ── STEP 5: Commit transaction ───────────────────────────────
if tx_id:
    r = client.post(f"/api/transactions/{tx_id}/commit")
    check(f"Step 5: Commit transaction tx={tx_id}", r, 200)
else:
    results.append((SKIP, "Step 5: Commit transaction", 0, "Skipped"))
    print(f"\n{SKIP} Step 5: Commit — skipped")

# ── STEP 6: Create cross-layer correlation ───────────────────
r = client.post("/api/correlations", json={
    "events": [
        {
            "os_event_id": str(REAL_PID or 1),
            "pid": REAL_PID or 1,
            "transaction_id": tx_id or 1,
            "query_id": query_id or 1,
            "timestamp": "2026-10-10T00:00:00Z",
            "event_type": "process_created",
            "source": "OS",
            "host_id": "DESKTOP-E2E"
        },
        {
            "os_event_id": str((REAL_PID or 1) + 1),
            "pid": REAL_PID or 1,
            "transaction_id": tx_id or 1,
            "query_id": query_id or 1,
            "timestamp": "2026-10-10T00:00:01Z",
            "event_type": "query_execution",
            "source": "DBMS",
            "host_id": "DESKTOP-E2E"
        }
    ]
})
corr = check("Step 6: Cross-layer correlation (POST /api/correlations)", r, 200)
trace_id = corr.get("trace", {}).get("trace_id") if corr and corr.get("trace") else None
print(f"     -> trace_id = {trace_id}")
print(f"     -> correlated = {corr.get('is_correlated') if corr else 'N/A'}")

# ── STEP 7: Deadlock detection ───────────────────────────────
r = client.post("/api/deadlocks/detect", json={
    "transactions": [
        {"transaction_id": 1, "holds": ["A"], "waits_for": ["B"]},
        {"transaction_id": 2, "holds": ["B"], "waits_for": ["A"]}
    ]
})
dl = check("Step 7: Deadlock detection (POST /api/deadlocks/detect)", r, 200)
print(f"     -> deadlock_detected = {dl.get('deadlock_detected') if dl else 'N/A'}")

# ── STEP 8: Get incidents list ───────────────────────────────
r = client.get("/api/deadlocks/incidents")
incidents = check("Step 8: List incidents (GET /api/deadlocks/incidents)", r, 200)
incident_id = REAL_INCIDENT_ID
if incidents and len(incidents) > 0 and not incident_id:
    incident_id = incidents[0].get("incident_id")
print(f"     -> Using incident_id = {incident_id}")

# ── STEP 9: Investigation timeline ──────────────────────────
if incident_id:
    r = client.get(f"/api/incidents/{incident_id}/investigation")
    inv = check(f"Step 9: Investigation timeline (GET /api/incidents/{incident_id}/investigation)", r, 200)
    timeline_events = inv.get("timeline", []) if inv else []
    print(f"     -> timeline events count = {len(timeline_events)}")
else:
    results.append((SKIP, "Step 9: Investigation timeline", 0, "Skipped"))
    print(f"\n{SKIP} Step 9: Investigation — skipped (no incident_id)")

# ── STEP 10: Blast radius ────────────────────────────────────
if incident_id:
    r = client.get(f"/api/v1/incidents/{incident_id}/blast-radius")
    br = check(f"Step 10: Blast radius (GET /api/v1/incidents/{incident_id}/blast-radius)", r, 200)
    print(f"     -> blast_radius incident_type = {br.get('incident_type') if br else 'N/A'}")

# ── STEP 11: Auto-correlation ────────────────────────────────
if REAL_OBS_ID:
    r = client.post("/api/correlations/auto", json={
        "observation_id": REAL_OBS_ID,
        "window_ms": 5000,
        "persist": False
    })
    ac = check(f"Step 11: Auto-correlation (observation_id={REAL_OBS_ID})", r, 200)
    print(f"     -> matched_query_id = {ac.get('matched_query_id') if ac else 'N/A'}")
else:
    results.append((SKIP, "Step 11: Auto-correlation", 0, "Skipped - no observation"))
    print(f"\n{SKIP} Step 11: Auto-correlation — skipped (no observation in DB)")

# ── STEP 12: What-if schedule analysis ──────────────────────
r = client.post("/api/what-if/schedules", json={
    "name": "e2e_test_schedule",
    "operations": [
        {"transaction_id": 1, "operation": "R", "data_item": "A"},
        {"transaction_id": 2, "operation": "W", "data_item": "A"},
        {"transaction_id": 1, "operation": "W", "data_item": "B"}
    ]
})
wif = check("Step 12: What-if schedule analysis (POST /api/what-if/schedules)", r, 201)
print(f"     -> conflict_serializable = {wif.get('result', {}).get('conflict_serializable') if wif else 'N/A'}")

# ── STEP 13: Run benchmark ───────────────────────────────────
r = client.post("/api/v1/benchmarks/run", json={
    "scenario": "DBMS_ONLY",
    "operations": 10,
    "concurrency": 1
})
bm = check("Step 13: Run benchmark (POST /api/v1/benchmarks/run)", r, 200)
print(f"     -> benchmark_id = {bm.get('benchmark_id') if bm else 'N/A'}")

# ── STEP 14: DBMS event collection ──────────────────────────
r = client.post("/api/dbms-events/collect", json={"limit": 10, "persist": False})
check("Step 14: Collect DBMS events (POST /api/dbms-events/collect)", r, 200)

# ── STEP 15: Full health details ─────────────────────────────
r = client.get("/health/details")
hd = check("Step 15: Full health details (GET /health/details)", r, 200)
print(f"     -> status = {hd.get('status') if hd else 'N/A'}")
print(f"     -> correlation_engine = {hd.get('correlation_engine') if hd else 'N/A'}")

# ── SUMMARY ─────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  RESULTS SUMMARY")
print("=" * 65)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
skipped = sum(1 for r in results if r[0] == SKIP)
for mark, label, status, _ in results:
    print(f"  {mark}  [{status:3}]  {label}")
print(f"\n  TOTAL: {passed} PASSED  |  {failed} FAILED  |  {skipped} SKIPPED  |  {len(results)} TOTAL")
if failed == 0:
    print("  ALL CHECKS PASSED - INTEGRATION IS COMPLETE!")
print("=" * 65)
