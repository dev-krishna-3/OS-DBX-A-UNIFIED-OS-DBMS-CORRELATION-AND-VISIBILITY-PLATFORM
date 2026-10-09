"""Persistence for raw DBMS query observations."""

from app.models.dbms_observations import DBMSQueryObservation


class DBMSObservationRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def insert_many(self, observations: list[DBMSQueryObservation]) -> list[DBMSQueryObservation]:
        if not observations:
            return []

        cursor = self.connection.cursor()
        persisted: list[DBMSQueryObservation] = []
        try:
            for observation in observations:
                cursor.execute(
                    """
                    INSERT INTO dbms_query_observations
                        (source_thread_id, source_event_id, connection_id,
                         processlist_user, database_name, query_type, query_text,
                         execution_time_ms, rows_affected, status, observed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE observation_id = LAST_INSERT_ID(observation_id)
                    """,
                    (
                        observation.source_thread_id,
                        observation.source_event_id,
                        observation.connection_id,
                        observation.processlist_user,
                        observation.database_name,
                        observation.query_type,
                        observation.query_text,
                        observation.execution_time_ms,
                        observation.rows_affected,
                        observation.status,
                        observation.observed_at,
                    ),
                )
                observation_id = int(cursor.lastrowid)
                # Keep query-level performance data available even when no
                # cross-layer trace has been established yet.
                if cursor.rowcount == 1:
                    cursor.execute(
                        """
                        INSERT INTO performance_records
                            (trace_id, metric_name, metric_value, recorded_at)
                        VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)
                        """,
                        (
                            None,
                            "dbms.query.execution_time_ms",
                            observation.execution_time_ms,
                            observation.observed_at,
                            None,
                            "dbms.query.rows_affected",
                            observation.rows_affected,
                            observation.observed_at,
                        ),
                    )
                persisted.append(
                    observation.model_copy(update={"observation_id": observation_id})
                )
            self.connection.commit()
            return persisted
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def recent(self, limit: int = 50) -> list[DBMSQueryObservation]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT observation_id, source_thread_id, source_event_id,
                       connection_id, processlist_user, database_name,
                       query_type, query_text, execution_time_ms,
                       rows_affected, status, observed_at
                FROM dbms_query_observations
                ORDER BY observed_at DESC, observation_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [DBMSQueryObservation(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()
