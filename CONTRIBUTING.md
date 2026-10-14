# OS-DBX Contributor & Development Guidelines

Welcome to the **OS-DBX: Unified OS-DBMS Correlation and Visibility Platform** repository!

This document outlines team guidelines, git branching conventions, testing practices, and zero-risk database safety protocols for contributing to the OS-DBX codebase.

---

## 1. Zero-Risk Engineering Principles

To protect all teammates' ongoing work and prevent database corruption or downtime:

1. **Never commit directly to `main` or `develop`**:
   - Always create and work on your own isolated feature branch:
     ```bash
     git checkout -b feature/<your-feature-name>
     ```
2. **Never modify existing database migrations or core schema directly**:
   - The production schema is defined in `database/schema.sql`.
   - Never alter previous migration files in `database/migrations/`.
   - Any new table or column must be introduced via a new incremental migration script (e.g. `003_add_feature.sql`).
3. **Keep Local Tests Isolated (In-Memory Mode)**:
   - When running unit tests locally or in CI pipelines, ensure `EVENT_STORAGE=memory`.
   - This prevents test runs from wiping or polluting the local development `os_dbx` database.

---

## 2. Environment Verification

We provide a non-destructive system diagnostics utility to verify your local Python environment, installed packages, and MySQL setup before starting development:

```bash
# Run basic environment check
python tools/system_diagnostics.py

# Run check without attempting MySQL connection
python tools/system_diagnostics.py --skip-db
```

---

## 3. Git Workflow & Collaboration

### Branching Convention
- `main`: Production-ready, stable releases only.
- `develop`: Integration branch where all feature PRs are merged.
- `feature/<module>-<description>`: Dedicated branches for individual teammates (e.g. `feature/os-collector`, `feature/dbms-query-tracking`, `feature/ci-diagnostics`).

### Step-by-Step Contribution Workflow

1. **Pull the latest changes**:
   ```bash
   git checkout develop
   git pull origin develop
   ```

2. **Create your feature branch**:
   ```bash
   git checkout -b feature/<your-topic>
   ```

3. **Verify Python compilation & syntax**:
   ```bash
   python -m compileall backend os_monitor cli.py
   ```

4. **Run tests**:
   ```bash
   # Set in-memory storage for test isolation
   pytest -v backend/tests
   ```

5. **Commit your changes**:
   ```bash
   git add <your-modified-files>
   git commit -m "feat(<module>): clear description of your contribution"
   ```

6. **Push to your branch and open a Pull Request**:
   ```bash
   git push origin feature/<your-topic>
   ```

---

## 4. Architecture and Teammate Track Ownership

| Track | Primary Modules | Primary Responsibilities |
|---|---|---|
| **Backend & DBMS Core** | `backend/app/`, `database/` | FastAPI APIs, MySQL Performance Schema collector, deadlocks, recovery what-if scenarios, correlation engine. |
| **OS Live Monitoring** | `os_monitor/` | Process monitor, resource monitor, filesystem monitor emitting shared `os_events`. |
| **Frontend & Visualization** | `frontend/` (separate track) | React dashboard for live observations, replay timelines, and correlation graphs. |
| **DevOps & QA** | `.github/workflows/`, `tools/` | Automated CI testing, linting, diagnostic utilities, and documentation. |

---

## 5. MySQL Performance Schema Requirements

For live DBMS query tracking and metrics:
- Ensure the Performance Schema consumer is enabled in MySQL:
  ```sql
  UPDATE performance_schema.setup_consumers
  SET ENABLED = 'YES'
  WHERE NAME = 'events_statements_history_long';
  ```
- Verify status with:
  ```bash
  python tools/system_diagnostics.py
  ```

Thank you for contributing to OS-DBX!
