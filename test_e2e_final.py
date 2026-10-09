"""
OS-DBX Phase 2 - Full End-to-End Verification Script
Tests the entire backend stack: Auth + Protected APIs + Live DB Data

Run with:  backend\venv\Scripts\python.exe test_e2e_final.py
           (from project root, with backend server running on port 8000)
"""
import requests
import sys
import random
import string

BASE_URL = "http://127.0.0.1:8000"
PASS_MARK = "[PASS]"
FAIL_MARK = "[FAIL]"
results = []

def check(label, condition, detail=""):
    status = PASS_MARK if condition else FAIL_MARK
    msg = f"  {status} {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append((label, condition))
    return condition

def section(title):
    print(f"\n{'='*58}")
    print(f"  {title}")
    print(f"{'='*58}")

# ─────────────────────────────────────────────────────────
section("1. Backend Health Check")
# ─────────────────────────────────────────────────────────
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    check("Backend is reachable", r.status_code == 200, r.text.strip())

    r2 = requests.get(f"{BASE_URL}/health/details", timeout=5)
    svc = r2.json().get("service", "?") if r2.status_code == 200 else "?"
    check("Health details endpoint", r2.status_code == 200, f"service={svc}")
except requests.ConnectionError:
    check("Backend is reachable", False, "Cannot connect to http://127.0.0.1:8000")
    print("\n  FATAL: Backend is not running. Start it with:")
    print("    cd backend && .\\venv\\Scripts\\python.exe -m uvicorn app.main:app --reload")
    sys.exit(1)

# ─────────────────────────────────────────────────────────
section("2. Authentication: Register & Login")
# ─────────────────────────────────────────────────────────
rand_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
test_user = f"e2e_{rand_suffix}"
test_pass = "TestPass123abc"
test_uid  = random.randint(10000, 99999)

r_reg = requests.post(f"{BASE_URL}/api/auth/register", json={
    "username": test_user,
    "uid_linux": test_uid,
    "password": test_pass
}, timeout=10)
check("Register new user (201)", r_reg.status_code == 201,
      f"user={test_user}" if r_reg.status_code == 201 else r_reg.text[:100])

# Duplicate should be rejected
r_dup = requests.post(f"{BASE_URL}/api/auth/register", json={
    "username": test_user,
    "uid_linux": test_uid + 1,
    "password": test_pass
}, timeout=10)
check("Duplicate username rejected (400)", r_dup.status_code == 400)

# Correct login
r_login = requests.post(f"{BASE_URL}/api/auth/token", data={
    "username": test_user,
    "password": test_pass
}, timeout=10)
ok_login = check("Login with correct credentials (200)", r_login.status_code == 200)

token = r_login.json().get("access_token") if ok_login else None
headers = {"Authorization": f"Bearer {token}"} if token else {}

# Wrong password should be rejected
r_bad = requests.post(f"{BASE_URL}/api/auth/token", data={
    "username": test_user,
    "password": "wrongpassword"
}, timeout=10)
check("Login with wrong password rejected (401)", r_bad.status_code == 401)

# ─────────────────────────────────────────────────────────
section("3. Authorization Guard (JWT Protection)")
# ─────────────────────────────────────────────────────────
# These endpoints must return 401 without a valid token
guarded_get_endpoints = [
    ("DBMS Observations",    f"{BASE_URL}/api/dbms-events/observations?limit=3"),
    ("Deadlock Incidents",   f"{BASE_URL}/api/deadlocks/incidents?limit=3"),
    ("OS Event Metrics",     f"{BASE_URL}/api/os-events/metrics"),
    ("Performance Records",  f"{BASE_URL}/api/performance/records?limit=3"),
    ("Events",               f"{BASE_URL}/api/events"),
    ("What-If Scenarios",    f"{BASE_URL}/api/what-if/scenarios"),
]

for name, url in guarded_get_endpoints:
    r = requests.get(url, timeout=5)
    check(f"Unauthenticated -> 401 [{name}]", r.status_code == 401,
          f"got {r.status_code}" if r.status_code != 401 else "")

# ─────────────────────────────────────────────────────────
section("4. Authenticated Data Access (Live DB Read)")
# ─────────────────────────────────────────────────────────
if token:
    # /me - verify user identity
    r_me = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=5)
    check("/api/auth/me returns current user", r_me.status_code == 200,
          f"user={r_me.json().get('username','?')}" if r_me.status_code == 200 else r_me.text[:60])

    # DBMS Observations — reads from MySQL performance_schema data
    r_obs = requests.get(f"{BASE_URL}/api/dbms-events/observations?limit=5", headers=headers, timeout=5)
    n_obs = len(r_obs.json()) if r_obs.status_code == 200 else "?"
    check("DBMS Observations (authenticated, live DB)", r_obs.status_code == 200, f"rows={n_obs}")

    # Deadlock incidents
    r_dl = requests.get(f"{BASE_URL}/api/deadlocks/incidents?limit=5", headers=headers, timeout=5)
    n_dl = len(r_dl.json()) if r_dl.status_code == 200 else "?"
    check("Deadlock Incidents (authenticated, live DB)", r_dl.status_code == 200, f"rows={n_dl}")

    # Performance records
    r_perf = requests.get(f"{BASE_URL}/api/performance/records?limit=5", headers=headers, timeout=5)
    n_perf = len(r_perf.json()) if r_perf.status_code == 200 else "?"
    check("Performance Records (authenticated)", r_perf.status_code == 200, f"rows={n_perf}")

    # OS Event Metrics (event stream health)
    r_metrics = requests.get(f"{BASE_URL}/api/os-events/metrics", headers=headers, timeout=5)
    check("OS Events Metrics (authenticated)", r_metrics.status_code == 200,
          f"got {r_metrics.status_code}" if r_metrics.status_code != 200 else "ok")

    # Events
    r_ev = requests.get(f"{BASE_URL}/api/events", headers=headers, timeout=5)
    check("Events list (authenticated)", r_ev.status_code == 200,
          f"got {r_ev.status_code}" if r_ev.status_code != 200 else "ok")

    # What-If Scenarios
    r_wi = requests.get(f"{BASE_URL}/api/what-if/scenarios", headers=headers, timeout=5)
    check("What-If Scenarios (authenticated)", r_wi.status_code == 200,
          f"got {r_wi.status_code}" if r_wi.status_code != 200 else "ok")

    # Blast radius - requires a valid incident ID (use 1 as probe)
    r_br = requests.get(f"{BASE_URL}/api/v1/incidents/1/blast-radius", headers=headers, timeout=5)
    check("Blast Radius (authenticated, probe incident=1)",
          r_br.status_code in (200, 404),  # 404 = no incident with ID 1, which is ok
          f"status={r_br.status_code}")
else:
    print("  SKIPPED (no token — login step failed)")

# ─────────────────────────────────────────────────────────
section("5. Public Endpoints Remain Open (no auth needed)")
# ─────────────────────────────────────────────────────────
r_demo = requests.get(f"{BASE_URL}/api/demo/correlation", timeout=5)
check("Demo correlation (public)", r_demo.status_code == 200)

r_root = requests.get(f"{BASE_URL}/", timeout=5)
check("Root endpoint (public)", r_root.status_code == 200)

r_docs = requests.get(f"{BASE_URL}/docs", timeout=5)
check("Swagger /docs (public)", r_docs.status_code == 200)

# ─────────────────────────────────────────────────────────
section("Summary")
# ─────────────────────────────────────────────────────────
total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed

print(f"\n  Results: {passed}/{total} checks passed")
if failed > 0:
    print("\n  Failed checks:")
    for label, ok in results:
        if not ok:
            print(f"    {FAIL_MARK} {label}")
    sys.exit(1)
else:
    print("\n  ALL CHECKS PASSED - Phase 2 backend is fully operational!")
    print(f"  Backend:  {BASE_URL}")
    print(f"  API Docs: {BASE_URL}/docs")
    print(f"  CLI Tool: python cli.py")
print()
