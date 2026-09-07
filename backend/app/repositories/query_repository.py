"""Parameterized MySQL persistence for query execution events."""

from app.models.query_executions import DBMSEvent
from app.repositories.transaction_repository import (
    TransactionNotFoundError,
    TransactionStateError,
)


class TransactionPIDMismatchError(Exception):
    """Raised when a query PID does not belong to its transaction."""


class QueryRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def record_query(self, event: DBMSEvent) -> int:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT pid, status
                FROM transactions
                WHERE transaction_id = %s
                FOR UPDATE
                """,
                (event.transaction_id,),
            )
            transaction = cursor.fetchone()
            if transaction is None:
                raise TransactionNotFoundError(event.transaction_id)
            if transaction["status"] != "ACTIVE":
                raise TransactionStateError(
                    f"Transaction {event.transaction_id} is {transaction['status']}, not ACTIVE"
                )
            if transaction["pid"] != event.pid:
                raise TransactionPIDMismatchError(
                    f"PID {event.pid} is not associated with transaction {event.transaction_id}"
                )

            cursor.execute(
                """
                INSERT INTO query_executions
                    (transaction_id, pid, query_type, query_text,
                     execution_time_ms, rows_affected, status, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.transaction_id,
                    event.pid,
                    event.query_type,
                    event.query_text,
                    event.execution_time_ms,
                    event.rows_affected,
                    event.status,
                    event.timestamp,
                ),
            )
            query_id = cursor.lastrowid
            self.connection.commit()
            return query_id
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()
