# OS-DBX

OS-DBX is a forensic observability and correlation platform for investigating operating-system and database activity. It collects process, filesystem, resource, and database events, then correlates them when the available identifiers and timing support a relationship.

## What OS-DBX can establish

The correlation result depends on what evidence is available:

- **Direct correlation** uses matching identifiers such as a process ID and an inspected database socket/connection.
- **Temporal correlation** reports activity that occurred within a configured time window. Timing by itself does not prove that one event caused another.
- **Not correlated** means the system has no supported link for the events in question.

Treat these as investigative observations. The current application does not provide a tamper-evident chain of custody, signed evidence packages, immutable/WORM storage, or a legal determination that an event is admissible evidence. Preserve original host and database logs separately when an investigation requires those properties.

## Collection modes and deployment limits

Choose the deployment based on the machine OS-DBX must observe:

| Mode | What it observes | Important limit |
|---|---|---|
| Native Windows backend | The Windows host running the backend, including the collector's process and filesystem events and the host's available socket/process information | The backend still requires MySQL for account initialization and application features. The collector needs suitable OS permissions. Validate socket visibility and database placement in the actual environment. |
| Docker Compose | The application containers and events explicitly sent to its authenticated ingest API | A container does not automatically see the Windows host's processes, files, or sockets. The Compose stack does not start the separate host agent. |
| Remote host agent | Events the configured agent can collect on its host and send to the backend | The host agent and backend need network connectivity and the same dedicated ingest token. An agent's event feed does not by itself provide host socket-to-database correlation. |

For host-level Windows collection with a Docker-hosted backend, run the agent on the Windows host and configure it to send to the backend. Keep the agent token private. Confirm that required process, filesystem, and socket sources are actually available before relying on an investigation result.

## Architecture

```text
Windows host collector or remote agent ── authenticated event ingest ──┐
                                                                       v
Browser ── frontend / same-origin API proxy ── FastAPI backend ── MySQL
                                                ├─ authentication and roles
                                                ├─ event and audit APIs
                                                ├─ correlation services
                                                └─ simulation and analysis labs
```

The frontend is React, TypeScript, and Vite. The API uses FastAPI and bearer tokens. The backend requires MySQL for account initialization and application data. `EVENT_STORAGE` controls OS-event persistence: `mysql` stores those records in MySQL; `memory` keeps only a bounded recent set that does not survive a backend restart.

## Security and data handling

- Production startup requires a non-root MySQL account, database password, administrator password, JWT signing key, MySQL event storage, and a dedicated OS agent token.
- Public account registration is off by default. Admin-only areas include the audit log, SQL console, bridge live map, and benchmark execution.
- Browser access tokens are kept in session storage and expire after 12 hours. This limits persistence after the browser session ends; it does not protect an already compromised browser session.
- Login/signup throttling is in-process, so it is not shared between multiple backend workers or replicas.
- Operational records are shared within the OS-DBX workspace. The database does not enforce per-user or per-tenant isolation.
- The Compose MySQL data volume persists across container restarts. Protect backups and the host volume as sensitive investigative data. Define and enforce a retention policy appropriate to your environment; the application does not provide a complete evidence-retention or immutable-archive system.
- The endpoint agent's retry queue is in memory. Events still queued when the agent process exits are not a durable local evidence store.
- A database password was removed from tracked diagnostic scripts, but old Git history is not rewritten. Rotate it if it was ever valid.

For step-by-step instructions on running either the in-memory prototype or the production Docker Compose stack, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Local development

### Requirements

- Python 3.12 or later
- Node.js 20 or later and npm
- MySQL 8.0, if using MySQL-backed features

### Database

Initialize a development database with the project schema. In Windows Command Prompt (not PowerShell):

```cmd
mysql -u root -p < database/schema.sql
```

Create a least-privilege application user for the backend and grant it access to the development database. Do not run the application as MySQL root. Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` in `backend/.env` as needed. The user needs the database permissions required by the application; grant any additional Performance Schema visibility separately and only if the chosen collection features require it.

### Backend

From the repository root:

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ADMIN_PASSWORD = "use-a-private-development-password"
$env:JWT_SECRET_KEY = "use-a-long-random-development-key"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive API docs are available at `/docs` in development. For a database-backed local run, set `EVENT_STORAGE=mysql` and configure MySQL before starting the backend; otherwise OS events use memory storage.

The backend creates the `admin` account from `ADMIN_PASSWORD`; whenever that variable is set, startup resets the account password to that value. Keep it private and stable across restarts unless you intend to rotate the admin password. New account passwords must be at least 12 characters. Public registration is disabled unless `ALLOW_PUBLIC_REGISTRATION=true` is explicitly configured.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`. Set `VITE_API_BASE_URL` only when the API is served at a different origin and the backend CORS allowlist is configured for that origin. The default is same-origin API access, which is proxied by the Docker Nginx configuration.

## Docker Compose

The Compose configuration builds the frontend and backend, initializes MySQL from `database/schema.sql` on a new data volume, and stores database data in the `mysql_data` volume. The frontend Nginx server proxies `/api/` to the backend. MySQL is not published on the host; the backend API and frontend are published on ports 8000 and 5173.

1. Copy `.env.example` to `.env`.
2. Set unique, strong values for `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `ADMIN_PASSWORD`, and `JWT_SECRET_KEY`. Keep `.env` private and out of source control.
3. Leave `CORS_ORIGINS=[]` when using the same-origin frontend proxy. Set a JSON array of trusted origins only if browser clients will access the API from other origins.
4. Start the stack:

```powershell
docker compose up -d --build
```

Open the frontend at `http://localhost:5173`; the API is also published at `http://localhost:8000`. These HTTP endpoints are intended for local access. For public hosting, put the services behind a properly configured HTTPS reverse proxy or platform ingress, restrict direct API access as appropriate, and configure trusted origins and secret storage for that hosting environment.

On an existing MySQL data volume, the MySQL container's initialization variables and schema scripts do not recreate or update database users/schema. Before upgrading, back up the data and verify the `osdbx_app` user exists with the required database permissions. Do not remove the volume as a troubleshooting step unless you intend to destroy its data.

The Compose stack does not run the Windows host collector. Device enrollment now issues a dedicated, expiring bearer credential; configure the collector with the enrolled device's credential and reachable HTTPS API URL. Do not use a human administrator token for ingestion. The current collector does not yet implement protected credential storage or the agreed durable encrypted queue, so it is not ready for pilot use.

## Before a real investigation or public deployment

- The deployment plan at [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) defines 16 mandatory outage, security, recovery, and evidence-integrity scenarios. They are not yet verified. Do not consider the project production-ready until each scenario has an implemented detection/response, a recovery procedure, and a recorded passing test.
- Select the deployment topology based on which host and database must be observed; remote/cloud hosting alone cannot inspect another machine's local kernel state.
- Verify collector permissions, event sources, timestamps, host identity, socket visibility, and database connectivity on the actual target machines.
- Configure HTTPS, firewall/network access, secret management, backups, retention, and monitoring for the chosen host.
- Restrict access to collected process, path, query, and audit data; it can contain sensitive information.
- Establish separate preservation controls if the investigation requires tamper evidence, chain of custody, or immutable retention. Current project behavior does not provide legally defensible chain of custody.
- Run the project's backend tests and frontend production build in the target environment before relying on a release. Their results are not asserted here.

## Troubleshooting

- **401/session expired:** Sign in again. There are no quick-fill demo credentials.
- **MySQL connection failure:** Check the backend database host, application username, password, schema, and grants. For an existing Compose volume, check that `osdbx_app` was provisioned; initialization only applies to a new volume.
- **No Windows host events in Docker:** The Compose stack observes its containers. Run and configure the host agent separately to forward host events.
- **No durable OS-event history:** Check that `EVENT_STORAGE=mysql` is selected and that the backend database schema and grants are valid. Memory mode is cleared when the backend restarts.
- **Cannot inspect host sockets:** Run the relevant collector where those sockets are visible and verify OS permissions. Forwarded event data alone does not guarantee direct socket correlation.
