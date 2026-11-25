"""Poll completed MySQL statements from Performance Schema."""

from datetime import datetime, timezone
from typing import Any

from app.models.dbms_observations import DBMSQueryObservation


STATEMENT_HISTORY_QUERY = """
SELECT
    recent.THREAD_ID,
    recent.EVENT_ID,
    recent.PROCESSLIST_ID,
    recent.PROCESSLIST_USER,
    recent.CURRENT_SCHEMA,
    recent.SQL_TEXT,
    recent.TIMER_WAIT,
    recent.ROWS_AFFECTED,
    recent.MYSQL_ERRNO
FROM (
    SELECT
        statements.THREAD_ID,
        statements.EVENT_ID,
        threads.PROCESSLIST_ID,
        threads.PROCESSLIST_USER,
        statements.CURRENT_SCHEMA,
        statements.SQL_TEXT,
        statements.TIMER_WAIT,
        statements.ROWS_AFFECTED,
        statements.MYSQL_ERRNO,
        statements.TIMER_START
    FROM performance_schema.events_statements_history_long AS statements
    LEFT JOIN performance_schema.threads AS threads
        ON threads.THREAD_ID = statements.THREAD_ID
    WHERE statements.SQL_TEXT IS NOT NULL
      AND (threads.PROCESSLIST_ID IS NULL OR threads.PROCESSLIST_ID <> %s)
      -- Do not collect the collector's own persistence and polling statements.
      AND LOWER(statements.SQL_TEXT) NOT LIKE '%dbms_query_observations%'
      AND LOWER(statements.SQL_TEXT) NOT LIKE '%events_statements_history%'
      AND LOWER(statements.SQL_TEXT) NOT LIKE '%setup_consumers%'
      AND LOWER(statements.SQL_TEXT) NOT LIKE '%session_connect_attrs%'
    ORDER BY statements.TIMER_START DESC
    LIMIT %s
) AS recent
ORDER BY recent.THREAD_ID, recent.EVENT_ID
"""

STATEMENT_HISTORY_SHORT_QUERY = STATEMENT_HISTORY_QUERY.replace(
    "performance_schema.events_statements_history_long",
    "performance_schema.events_statements_history",
)


def _value(row: Any, key: str, index: int):
    if isinstance(row, dict):
        return row.get(key)
    return row[index]


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _query_type(sql_command: Any, query_text: str) -> str:
    command = _text(sql_command).strip().upper() if sql_command else ""
    if command:
        return command[:50]
    return query_text.lstrip().split(maxsplit=1)[0].upper()[:50]


class MySQLQueryCollector:
    """Collect external statements while keeping per-thread watermarks."""

    def __init__(
        self,
        connection,
        seen_event_ids: dict[int, int] | None = None,
        seen_processlist_queries: set | None = None,
    ) -> None:
        self.connection = connection
        self._seen_event_ids: dict[int, int] = (
            seen_event_ids if seen_event_ids is not None else {}
        )
        self._seen_processlist_queries: set = (
            seen_processlist_queries if seen_processlist_queries is not None else set()
        )
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT CONNECTION_ID()")
            self._connection_id = int(cursor.fetchone()[0])
        finally:
            cursor.close()

    def poll_from_processlist(self, limit: int = 100) -> list[DBMSQueryObservation]:
        """Harvest active queries from information_schema.processlist when performance_schema is disabled."""
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO
                FROM information_schema.processlist
                WHERE INFO IS NOT NULL
                  AND ID <> %s
                  AND LOWER(INFO) NOT LIKE '%processlist%'
                  AND LOWER(INFO) NOT LIKE '%dbms_query_observations%'
                ORDER BY TIME DESC
                LIMIT %s
                """,
                (self._connection_id, limit),
            )
            observations: list[DBMSQueryObservation] = []
            for row in cursor.fetchall():
                query_text = _text(row.get("INFO") or "").strip()
                if not query_text:
                    continue
                conn_id = int(row.get("ID") or 0)
                event_key = (conn_id, query_text)
                if event_key in self._seen_processlist_queries:
                    continue
                self._seen_processlist_queries.add(event_key)
                if len(self._seen_processlist_queries) > 1000:
                    self._seen_processlist_queries.clear()

                time_secs = float(row.get("TIME") or 0)
                observations.append(
                    DBMSQueryObservation(
                        source_thread_id=conn_id,
                        source_event_id=conn_id,
                        connection_id=conn_id,
                        processlist_user=_text(row.get("USER") or "unknown"),
                        database_name=_text(row.get("DB") or "mysql"),
                        query_type=_query_type(None, query_text),
                        query_text=query_text,
                        execution_time_ms=time_secs * 1000.0,
                        rows_affected=0,
                        status="EXECUTING" if row.get("COMMAND") == "Query" else "SUCCESS",
                        observed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
            return observations
        except Exception:
            return []
        finally:
            cursor.close()

    def _rows_to_observations(self, rows: list[Any]) -> list[DBMSQueryObservation]:
        observations: list[DBMSQueryObservation] = []
        for row in rows:
            thread_id = int(_value(row, "THREAD_ID", 0))
            event_id = int(_value(row, "EVENT_ID", 1))
            if event_id <= self._seen_event_ids.get(thread_id, 0):
                continue

            query_text = _text(_value(row, "SQL_TEXT", 5)).strip()
            self._seen_event_ids[thread_id] = event_id
            if not query_text:
                continue

            timer_wait = _value(row, "TIMER_WAIT", 6) or 0
            mysql_errno = int(_value(row, "MYSQL_ERRNO", 8) or 0)
            observations.append(
                DBMSQueryObservation(
                    source_thread_id=thread_id,
                    source_event_id=event_id,
                    connection_id=_value(row, "PROCESSLIST_ID", 2),
                    processlist_user=_value(row, "PROCESSLIST_USER", 3),
                    database_name=_value(row, "CURRENT_SCHEMA", 4),
                    query_type=_query_type(None, query_text),
                    query_text=query_text,
                    execution_time_ms=float(timer_wait) / 1_000_000_000,
                    rows_affected=max(0, int(_value(row, "ROWS_AFFECTED", 7) or 0)),
                    status="SUCCESS" if mysql_errno == 0 else f"ERROR_{mysql_errno}",
                    observed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
        return observations

    def poll(self, limit: int = 100) -> list[DBMSQueryObservation]:
        try:
            cursor = self.connection.cursor(dictionary=True)
            try:
                cursor.execute(STATEMENT_HISTORY_QUERY, (self._connection_id, limit))
                rows = cursor.fetchall()
                if not rows:
                    try:
                        cursor.execute(
                            "UPDATE performance_schema.setup_consumers SET ENABLED = 'YES' "
                            "WHERE NAME IN ('events_statements_history_long', 'events_statements_history')"
                        )
                    except Exception:
                        pass
                    try:
                        cursor.execute(STATEMENT_HISTORY_SHORT_QUERY, (self._connection_id, limit))
                        rows = cursor.fetchall()
                    except Exception:
                        rows = []
                observations = self._rows_to_observations(rows)
                if observations:
                    return observations
                # If both statement history tables yielded 0 rows, check processlist for active queries
                if not rows:
                    return self.poll_from_processlist(limit=limit)
                return observations
            finally:
                cursor.close()
        except Exception:
            # Fall back to processlist polling if performance_schema is disabled or fails
            return self.poll_from_processlist(limit=limit)
