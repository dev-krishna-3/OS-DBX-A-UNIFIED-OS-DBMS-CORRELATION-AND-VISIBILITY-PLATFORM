"""Idempotent SQL schema bootstrapper for fresh Cloud MySQL deployments."""

from pathlib import Path
from typing import Iterable


def _find_database_dir() -> Path:
    """Locate the database/ directory across both repo and container layouts."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "database"
        if (candidate / "schema.sql").is_file():
            return candidate
    raise FileNotFoundError("Could not locate database/schema.sql")


def split_sql_statements(sql_text: str) -> list[str]:
    """Split a SQL script into individual statements, ignoring comments and respecting quotes."""
    statements: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    i = 0
    length = len(sql_text)

    while i < length:
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < length else ""

        if not in_single and not in_double:
            if ch == "#" or (ch == "-" and nxt == "-"):
                while i < length and sql_text[i] != "\n":
                    i += 1
                continue
            if ch == "/" and nxt == "*":
                i += 2
                while i + 1 < length and not (sql_text[i] == "*" and sql_text[i + 1] == "/"):
                    i += 1
                i += 2
                continue

        if ch == "'" and not in_double:
            if in_single and nxt == "'":
                buf.append("''")
                i += 2
                continue
            if not (buf and buf[-1] == "\\"):
                in_single = not in_single
        elif ch == '"' and not in_single:
            if not (buf and buf[-1] == "\\"):
                in_double = not in_double
        elif ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf.clear()
            i += 1
            continue

        buf.append(ch)
        i += 1

    trailing = "".join(buf).strip()
    if trailing:
        statements.append(trailing)
    return statements


def _execute_statements(cursor, statements: Iterable[str]) -> int:
    count = 0
    for stmt in statements:
        cursor.execute(stmt)
        count += 1
    return count


def init_schema_if_needed() -> dict[str, bool]:
    """Initialize schema.sql and workspace/device migration 003 if tables are missing."""
    from app.config.database import get_connection

    db_dir = _find_database_dir()
    conn = get_connection()
    cur = conn.cursor()
    applied_base = False
    applied_migration_003 = False
    try:
        cur.execute("SHOW TABLES LIKE 'users'")
        if cur.fetchone() is None:
            base_sql = (db_dir / "schema.sql").read_text(encoding="utf-8")
            _execute_statements(cur, split_sql_statements(base_sql))
            conn.commit()
            applied_base = True

        cur.execute("SHOW COLUMNS FROM processes LIKE 'workspace_id'")
        if cur.fetchone() is None:
            mig_003 = db_dir / "migrations" / "003_add_workspace_and_device_identity.sql"
            if mig_003.is_file():
                mig_sql = mig_003.read_text(encoding="utf-8")
                _execute_statements(cur, split_sql_statements(mig_sql))
                conn.commit()
                applied_migration_003 = True
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return {
        "applied_base_schema": applied_base,
        "applied_migration_003": applied_migration_003,
    }
