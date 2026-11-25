"""MySQL persistence for traces produced by the correlation service."""

from app.models.correlation import CorrelationResult


class CorrelationRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def persist(self, result: CorrelationResult) -> CorrelationResult:
        if not result.is_correlated or result.trace is None:
            return result

        cursor = self.connection.cursor()
        try:
            trace = result.trace
            cursor.execute(
                """
                INSERT INTO cross_layer_traces
                    (pid, transaction_id, status, started_at, ended_at, summary)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    trace.pid,
                    trace.transaction_id,
                    trace.status,
                    trace.started_at,
                    trace.ended_at,
                    trace.summary,
                ),
            )
            trace_id = int(cursor.lastrowid)
            for correlation in result.correlations:
                cursor.execute(
                    """
                    INSERT INTO event_correlations
                        (trace_id, os_event_id, db_event_id, query_id,
                         correlation_method, confidence_score, sequence_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        trace_id,
                        correlation.os_event_id,
                        correlation.db_event_id,
                        correlation.query_id,
                        correlation.correlation_method,
                        correlation.confidence_score,
                        correlation.sequence_order,
                    ),
                )
            self.connection.commit()
            return result.model_copy(
                update={
                    "trace": trace.model_copy(update={"trace_id": trace_id}),
                    "correlations": [
                        item.model_copy(update={"trace_id": trace_id})
                        for item in result.correlations
                    ],
                }
            )
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()
