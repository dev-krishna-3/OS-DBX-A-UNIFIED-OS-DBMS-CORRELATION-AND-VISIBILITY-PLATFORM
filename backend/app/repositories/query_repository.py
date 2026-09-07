"""Parameterized MySQL repository for ``query_executions``."""

from typing import Any

from app.models.events import DBMSEvent
from app.repositories.transaction_repository import (
    TransactionNotFoundError,
    TransactionPIDMismatchError,
    TransactionStateError,
)


class QueryRepository:
    """Persist query execution events using an injected MySQL connection."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def record_query(self, event: DBMSEvent) -> int:
        """Validate the transaction association and insert one query row."""

        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)

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

            transaction_pid = (
                transaction["pid"]
                if isinstance(transaction, dict)
                else transaction[0]
            )
            transaction_status = (
                transaction["status"]
                if isinstance(transaction, dict)
                else transaction[1]
            )

            if transaction_status != "ACTIVE":
                raise TransactionStateError(
                    f"Transaction {event.transaction_id} is "
                    f"{transaction_status}, not ACTIVE"
                )

            if int(transaction_pid) != event.pid:
                raise TransactionPIDMismatchError(
                    f"PID {event.pid} is not associated with "
                    f"transaction {event.transaction_id}"
                )

            cursor.execute(
                """
                INSERT INTO query_executions (
                    transaction_id,
                    pid,
                    query_type,
                    query_text,
                    execution_time_ms,
                    rows_affected,
                    status,
                    timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

            self.connection.commit()
            return int(cursor.lastrowid)

        except Exception:
            self.connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()
