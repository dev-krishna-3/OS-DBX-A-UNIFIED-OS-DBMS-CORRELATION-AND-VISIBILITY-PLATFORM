import requests
import json

base_url = "http://127.0.0.1:8000"

print("1. Registering user")
r_reg = requests.post(f"{base_url}/api/auth/register", json={
    "username": "cli_demo_user",
    "uid_linux": 9999,
    "password": "supersecurepassword"
})
print("Register response:", r_reg.status_code, r_reg.text)

print("\n2. Logging in")
r_login = requests.post(f"{base_url}/api/auth/token", data={
    "username": "cli_demo_user",
    "password": "supersecurepassword"
})
print("Login response:", r_login.status_code, r_login.text)

token = r_login.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

print("\n3. Testing unauthenticated endpoint (should fail)")
r_fail = requests.get(f"{base_url}/api/dbms-events/observations?limit=5")
print("Unauth response:", r_fail.status_code)

print("\n4. Testing authenticated endpoint (should succeed)")
r_success = requests.get(f"{base_url}/api/dbms-events/observations?limit=5", headers=headers)
print("Auth response:", r_success.status_code)

print("\n5. Fetching health (public)")
r_health = requests.get(f"{base_url}/health")
print("Health response:", r_health.status_code, r_health.text)

