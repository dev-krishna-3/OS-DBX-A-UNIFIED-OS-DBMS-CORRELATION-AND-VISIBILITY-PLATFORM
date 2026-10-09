"""Candidate lookup for automatic cross-layer correlation."""

from typing import Any


class AutoCorrelationRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def observation(self, observation_id: int) -> dict[str, Any] | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT observation_id, query_type, query_text, observed_at
                FROM dbms_query_observations
                WHERE observation_id = %s
                """,
                (observation_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()

    def matching_queries(
        self, observation: dict[str, Any], window_ms: int
    ) -> list[dict[str, Any]]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT query_id, transaction_id, pid, query_type, query_text,
                       timestamp
                FROM query_executions
                WHERE query_type = %s
                  AND query_text = %s
                  AND ABS(TIMESTAMPDIFF(MICROSECOND, timestamp, %s)) <= %s
                ORDER BY ABS(TIMESTAMPDIFF(MICROSECOND, timestamp, %s)), query_id
                """,
                (
                    observation["query_type"],
                    observation["query_text"],
                    observation["observed_at"],
                    window_ms * 1000,
                    observation["observed_at"],
                ),
            )
            return cursor.fetchall()
        finally:
            cursor.close()

    def matching_os_events(self, query: dict[str, Any], window_ms: int) -> list[dict[str, Any]]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT event_id, pid, event_type, timestamp
                FROM os_events
                WHERE pid = %s
                  AND ABS(TIMESTAMPDIFF(MICROSECOND, timestamp, %s)) <= %s
                ORDER BY timestamp, event_id
                """,
                (query["pid"], query["timestamp"], window_ms * 1000),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
