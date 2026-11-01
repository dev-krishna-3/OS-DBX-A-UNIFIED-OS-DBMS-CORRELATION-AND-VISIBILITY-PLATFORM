# OS-DBX Platform Deployment Guide

This guide provides end-to-end instructions for deploying the **OS-DBX Unified OS-DBMS Correlation and Visibility Platform**.

Choose the deployment model that fits your operational needs:

- **Option 1: Local / Prototype Deployment (Fast In-Memory Mode)**
  - *Best for:* Local feature development, running tests, exploring simulation labs, UI prototyping.
  - *Database:* Uses fast in-memory stores (`EVENT_STORAGE=memory`). No local MySQL installation or Docker daemon required.
  - *Time to run:* ~2 minutes.

- **Option 2: Production Containerized Deployment (Docker Compose + MySQL 8.0)**
  - *Best for:* Staging, team shared environments, or cloud VM hosting (e.g., Oracle Cloud Infrastructure Always Free, AWS, DigitalOcean).
  - *Database:* Full MySQL 8.0 persistence, multi-tenant workspace isolation, persistent volumes, and Nginx reverse proxy.
  - *Time to run:* ~5 minutes.

---

## Architecture Overview

```text
Target Host (Endpoint to Observe)
  └── Enterprise Collector (agent/osdbx_agent.py)
            │ Outbound HTTPS + Per-Device Bearer Token
            ▼
Public TLS Ingress (Caddy / Nginx Reverse Proxy)
  ├── Port 80/443 (Frontend SPA & /health routing)
  └── Proxied /api/* (FastAPI Backend)
            │
      FastAPI Backend (backend/app/)
            ├── Multi-Tenancy (Workspaces, device grants, RBAC)
            ├── Correlation Engine (Direct, Temporal, None)
            └── Simulation Labs (Three.js 3D WebGL viewers)
            │
      MySQL 8.0 Database (schema.sql + migration 003)
```

---

## Option 1: Local / Prototype Deployment (In-Memory Mode)

In this mode, the platform runs directly on your local system with in-memory storage for OS events, audit logs, and what-if scenarios. You do **not** need MySQL or Docker.

### 1. Prerequisites
- **Python:** 3.12 or later (Python 3.12–3.15 supported)
- **Node.js:** 20.x or later with `npm`
- **Git**

### 2. Backend Setup
From the repository root directory:

```powershell
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a Python virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
# source venv/bin/activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Set required development environment variables
$env:EVENT_STORAGE = "memory"
$env:ENVIRONMENT = "development"
$env:ADMIN_PASSWORD = "DevAdminPassword123!"
$env:JWT_SECRET_KEY = "dev-insecure-secret-key-at-least-32-chars-long"

# 5. Start the FastAPI backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> [!NOTE]
> The backend will be accessible at `http://127.0.0.1:8000`.
> In development mode, interactive Swagger API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
Open a new terminal window at the repository root:

```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

> [!TIP]
> Open your browser and navigate to **`http://localhost:5173`**.
> You can sign in using:
> - **Username:** `admin`
> - **Password:** `DevAdminPassword123!` (or the value set in `$env:ADMIN_PASSWORD`)

### 4. Running Backend Tests in Memory Mode
To run the automated test suite without a database:
```powershell
$env:EVENT_STORAGE = "memory"
backend\venv\Scripts\python.exe -m pytest backend/tests -q
```
*Expected result:* 122+ tests passed, 0 failures.

---

## Option 2: Production Containerized Deployment (Docker Compose)

In this mode, Docker Compose coordinates three private containers on an isolated Docker network:
1. **`os-dbx-mysql`**: MySQL 8.0 engine with persistent volumes, least-privilege `osdbx_app` user, and automatic schema initialization.
2. **`os-dbx-backend`**: FastAPI application with hardened security headers, rate limiting, and 1MB request body constraints.
3. **`os-dbx-frontend`**: Production Vite build served through high-performance Alpine Nginx, proxying `/api/` and `/health` requests to the backend.

### 1. Prerequisites
- Docker Engine 24+ and Docker Compose v2+
- A server or virtual machine (e.g. 1 OCPU, 2+ GB RAM, Ubuntu 22.04 LTS or Debian 12)

### 2. Configure Environment Secrets
From the repository root, copy the environment template to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and configure strong production secrets:

```ini
# MySQL root administration password
MYSQL_ROOT_PASSWORD=generate-a-strong-root-password-here

# MySQL application user password
MYSQL_PASSWORD=generate-a-strong-app-password-here

# Seeded OS-DBX platform admin password (minimum 12 characters)
ADMIN_PASSWORD=YourStrongPlatformAdminPassword2026!

# JWT token signing secret (minimum 32 characters)
JWT_SECRET_KEY=generate-a-cryptographically-random-32-char-key

# Set to true only if public user signups are permitted
ALLOW_PUBLIC_REGISTRATION=false

# Allowed external browser origins (e.g. ["https://osdbx.yourdomain.com"])
CORS_ORIGINS=["https://osdbx.yourdomain.com"]
```

> [!IMPORTANT]
> Never commit `.env` into source control. Keep production passwords private.

### 3. Launch the Stack
Start all services in detached mode:

```bash
docker compose up -d --build
```

### 4. Verify Service Health
Check container health and startup logs:

```bash
# Verify container statuses (all should be Up or Up (healthy))
docker compose ps

# Check backend logs
docker compose logs -f backend

# Verify health check endpoint
curl -f http://localhost:5173/health
```

The output of `curl http://localhost:5173/health` should be:
```json
{"status":"ok"}
```

Access the web interface at `http://<your-server-ip>:5173` (or port 80/443 if using a reverse proxy).

---

## Public HTTPS Ingress (Optional: Cloud / Free-Tier VM)

If deploying to a cloud host (such as an Oracle Cloud Always Free Ampere VM or AWS EC2), place **Caddy** in front of Docker Compose to provide automated TLS certificates:

### 1. Install Caddy
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLF 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLF 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

### 2. Configure `/etc/caddy/Caddyfile`
```caddyfile
osdbx.yourdomain.com {
    reverse_proxy localhost:5173

    encode gzip zstd
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

### 3. Restart Caddy
```bash
sudo systemctl reload caddy
```
Caddy will automatically provision and renew a free Let's Encrypt TLS certificate for your domain.

---

## Endpoint Collector Agent Deployment

The **OS-DBX Endpoint Agent** collects host-level processes, filesystem mutations, CPU/RAM telemetry, and heartbeat leases from authorized target machines.

### Step 1: Enroll Device in Dashboard
1. Sign in to the OS-DBX web interface as an Administrator or Workspace Owner.
2. Navigate to **Devices** > **Enroll New Device**.
3. Specify a display name and approved collection scope.
4. Copy the generated **Device Credential Token**.

### Step 2: Install Collector on Target Endpoint

#### On Windows:
Open Command Prompt (`cmd.exe`) in the `agent/` folder:

```cmd
install-agent.bat "https://osdbx.yourdomain.com" "<DEVICE_CREDENTIAL_TOKEN>"
```

*What this does:*
- Creates `config.json` with the target server URL and device token.
- Installs `psutil` and `watchdog`.
- Creates a silent startup task in Windows Task Scheduler (`OSDBX_Forensic_Agent`) to run on boot without console windows.
- Starts collection immediately.

#### On Linux or macOS:
Open terminal in the `agent/` folder:

```bash
chmod +x install-agent.sh uninstall-agent.sh
./install-agent.sh "https://osdbx.yourdomain.com" "<DEVICE_CREDENTIAL_TOKEN>"
```

*What this does:*
- Creates `config.json` with the target server URL and device token.
- Installs `psutil` and `watchdog`.
- Adds an `@reboot` crontab entry for automated persistent background monitoring.
- Launches the agent process in the background (`agent.pid`).

---

### Step 3: Verify Status & Heartbeat
- The agent sends a heartbeat every 30 seconds to `/api/devices/heartbeat`.
- Within 30 seconds of enrollment, the device status in the web dashboard will transition to **🟢 Online**.
- If a target endpoint goes offline:
  - After **60 seconds** (2 missed heartbeats), status marks as **🟡 Degraded**.
  - After **90 seconds** (3 missed heartbeats), status marks as **🔴 Offline**.

### Step 4: Uninstallation (Clean Teardown)
To cleanly stop collection and remove the background agent:

- **On Windows:**
  ```cmd
  uninstall-agent.bat
  ```
- **On Linux / macOS:**
  ```bash
  ./uninstall-agent.sh
  ```

---

## Troubleshooting & Verification

| Symptom | Cause | Solution |
|---|---|---|
| `HTTP 401 Unauthorized` during agent ingest | Missing or expired device credential | Re-enroll device in web UI or pass token when running `install-agent`. |
| `HTTP 413 Request body too large` | Payload exceeds 1MB limit | Bounded flush batches are enforced. Check `max_batch_size` in `config.json` (default: 25). |
| `Can't connect to MySQL server on 'db:3306'` | Database container still initializing | Ensure backend has `depends_on: db: condition: service_healthy` in Compose. |
| Device shows `Offline` in dashboard | Agent stopped or blocked by firewall | Verify agent is running via `agent.log` and ensure outbound HTTPS is open to the server. |
| Vite build `memory limit` | Node heap constrained during build | Build has been optimized. Run `npm run build` with Node 20+. |

---

## Release Verification Checklist

Before considering a production rollout complete, run the verification commands:

```bash
# 1. Run all backend tests
EVENT_STORAGE=memory pytest backend/tests -q

# 2. Test frontend production compile
cd frontend && npm run build

# 3. Test git formatting and whitespace clean check
git diff --check
```
