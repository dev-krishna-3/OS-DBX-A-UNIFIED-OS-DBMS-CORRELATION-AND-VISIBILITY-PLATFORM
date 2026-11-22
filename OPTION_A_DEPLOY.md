# Option A Split-Cloud Deployment Guide (Free, No Credit Card)

This `testing` workspace is configured for split cloud hosting:
- **Database:** Free Cloud MySQL (**Aiven MySQL** or **TiDB Cloud Serverless**)
- **Backend:** Free Docker Web Service (**Render** or **Hugging Face Spaces**)
- **Frontend:** Always-live Static Site (**Vercel** or **Cloudflare Pages**)
- **Agents:** `osdbx-agent.exe` on any Windows laptop pointing to your cloud backend URL

---

## Step 1 — Create Free Cloud MySQL (Aiven or TiDB Cloud)

### Option 1A: Aiven Free MySQL
1. Sign up at Aiven -> Create **MySQL** service -> select **Free** plan.
2. Copy from Service Overview:
   - `Host`, `Port`, `User` (e.g. `avnadmin`), `Password`, `Database` (e.g. `defaultdb`).
   - Download or copy the **CA Certificate** (`ca.pem` text).

### Option 1B: TiDB Cloud Serverless
1. Create a **TiDB Serverless** cluster -> create database `os_dbx` (or use `test`).
2. Copy `Host`, `Port` (`4000`), `User`, `Password`, and set `MYSQL_SSL_REQUIRED=true`.

> Because `AUTO_INIT_SCHEMA=true` is enabled in `render.yaml`, the backend automatically applies `database/schema.sql` and `database/migrations/003_add_workspace_and_device_identity.sql` on first startup if the database is empty.

---

## Step 2 — Deploy Backend on Render (Free Docker)

1. Push this `testing` folder to a separate test GitHub repository or branch.
2. In Render: **New + -> Blueprint** (uses `render.yaml`) or **New Web Service -> Docker** (`./Dockerfile.backend`, Free plan).
3. Fill in these environment variables:
   - `ENVIRONMENT=production`
   - `EVENT_STORAGE=mysql`
   - `AUTO_INIT_SCHEMA=true`
   - `ALLOW_PUBLIC_REGISTRATION=true`
   - `MYSQL_HOST=<your-db-host>`
   - `MYSQL_PORT=<your-db-port>`
   - `MYSQL_USER=<your-db-user>` (must not be `root`)
   - `MYSQL_PASSWORD=<your-db-password>`
   - `MYSQL_DATABASE=<your-db-name>`
   - `MYSQL_CONNECT_TIMEOUT=10`
   - `MYSQL_SSL_REQUIRED=true`
   - `MYSQL_SSL_CA_PEM=<paste Aiven ca.pem contents if using Aiven; leave empty for TiDB>`
   - `ADMIN_PASSWORD=<at least 12 characters>`
   - `JWT_SECRET_KEY=<at least 32 random characters>`
   - `CORS_ORIGINS=https://your-placeholder.vercel.app` (you will update this right after Step 3)
4. Wait until deploy passes and verify `https://<your-render-url>.onrender.com/health` returns `{"status":"ok"}`.

---

## Step 3 — Deploy Frontend on Vercel (Always Live)

1. In Vercel: **Add New Project** -> import the same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add Environment Variable:
   - `VITE_API_BASE_URL=https://<your-render-url>.onrender.com` (no trailing slash).
4. Deploy. Vercel builds `frontend/` using `frontend/vercel.json` SPA rewrites.
5. Copy your live Vercel URL (e.g. `https://osdbx-test.vercel.app`).
6. Go back to Render -> **Environment** -> set:
   - `CORS_ORIGINS=https://osdbx-test.vercel.app`
   and save (Render redeploys in ~1 minute).

---

## Step 4 — Test Login & Enroll Real Device Token for `osdbx-agent.exe`

1. Open `https://osdbx-test.vercel.app` and log in as `admin` with your `ADMIN_PASSWORD` (or register a new user).
2. Because `EVENT_STORAGE=mysql` is active, agents must use an enrolled device token instead of `dev-device-token`:
   - In the dashboard (or via `POST /api/devices`), enroll a device and copy the generated device token.
3. On any Windows laptop running `osdbx-agent.exe`, update `agent_config.json`:
   ```json
   {
     "server_url": "https://<your-render-url>.onrender.com",
     "api_token": "<enrolled-device-token>",
     "workspace_id": 1,
     "host_id": "laptop-1"
   }
   ```
4. Start `run-agent.bat` — telemetry streams directly to the cloud backend and persists in Cloud MySQL.
