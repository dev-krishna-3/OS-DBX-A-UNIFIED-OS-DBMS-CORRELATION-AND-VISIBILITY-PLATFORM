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
      AND LOWER(statements.SQL_TEXT) NOT LIKE '%events_statements_history_long%'
    ORDER BY statements.TIMER_START DESC
    LIMIT %s
) AS recent
ORDER BY recent.THREAD_ID, recent.EVENT_ID
"""


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

    def __init__(self, connection) -> None:
        self.connection = connection
        self._seen_event_ids: dict[int, int] = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT CONNECTION_ID()")
            self._connection_id = int(cursor.fetchone()[0])
        finally:
            cursor.close()

    def poll(self, limit: int = 100) -> list[DBMSQueryObservation]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(STATEMENT_HISTORY_QUERY, (self._connection_id, limit))
            observations: list[DBMSQueryObservation] = []
            for row in cursor.fetchall():
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
        finally:
            cursor.close()
