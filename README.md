# OS-DBX: Unified OS-DBMS Correlation and Visibility Platform

OS-DBX is a prototype for connecting operating-system events with database
transactions, queries, locks, and recovery workflows through cross-layer
traces. The backend uses Python, FastAPI, and MySQL. The OS collectors and
frontend are developed on separate teammate tracks.

## Project status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current implementation
status, verification evidence, teammate ownership, remaining work, and a
Claude prompt for preparing a status PDF and teammate handoff summary.

## Backend

See [backend/readme_backend.md](backend/readme_backend.md) for setup, runtime,
API endpoints, MySQL Performance Schema requirements, and collector instructions.

The FastAPI interactive API documentation is available at
`http://127.0.0.1:8000/docs` while the backend is running.

## Database and OS collector references

- Database schema: `database/schema.sql`
- Database migrations: `database/migrations/`
- Database design documents: `docs/`
- OS event collector: `os_monitor/README.md`
