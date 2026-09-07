"""Parameterized MySQL persistence for transaction lifecycle records."""

from datetime import datetime


class TransactionNotFoundError(Exception):
    """Raised when a transaction does not exist."""


class TransactionPIDMismatchError(ValueError):
    """Raised when a query PID differs from its transaction PID."""


class TransactionStateError(Exception):
    """Raised when a transaction is not in the required state."""


class TransactionRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def begin(self, pid: int, isolation_level: str, timestamp: datetime) -> int:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO transactions
                    (pid, status, start_time, isolation_level)
                VALUES (%s, %s, %s, %s)
                """,
                (pid, "ACTIVE", timestamp, isolation_level),
            )
            transaction_id = cursor.lastrowid
            self._insert_operation(
                cursor, transaction_id, "BEGIN", None, 1, timestamp
            )
            self.connection.commit()
            return transaction_id
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def add_operation(
        self,
        transaction_id: int,
        operation_type: str,
        data_item: str,
        timestamp: datetime,
    ) -> int:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT status FROM transactions WHERE transaction_id = %s FOR UPDATE",
                (transaction_id,),
            )
            transaction = cursor.fetchone()

            if transaction is None:
                raise TransactionNotFoundError(transaction_id)

            if transaction["status"] != "ACTIVE":
                raise TransactionStateError(
                    f"Transaction {transaction_id} is "
                    f"{transaction['status']}, not ACTIVE"
                )

            cursor.execute(
                """
                SELECT COALESCE(MAX(sequence_no), 0) + 1 AS next_sequence
                FROM transaction_operations
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )
            sequence_no = cursor.fetchone()["next_sequence"]

            self._insert_operation(
                cursor,
                transaction_id,
                operation_type,
                data_item,
                sequence_no,
                timestamp,
            )
            self.connection.commit()
            return sequence_no

        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def finish(
        self,
        transaction_id: int,
        status: str,
        timestamp: datetime,
    ) -> None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT status FROM transactions WHERE transaction_id = %s FOR UPDATE",
                (transaction_id,),
            )
            transaction = cursor.fetchone()

            if transaction is None:
                raise TransactionNotFoundError(transaction_id)

            if transaction["status"] != "ACTIVE":
                raise TransactionStateError(
                    f"Transaction {transaction_id} is "
                    f"{transaction['status']}, not ACTIVE"
                )

            cursor.execute(
                """
                SELECT COALESCE(MAX(sequence_no), 0) + 1 AS next_sequence
                FROM transaction_operations
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )
            sequence_no = cursor.fetchone()["next_sequence"]

            operation_type = (
                "COMMIT" if status == "COMMITTED" else "ROLLBACK"
            )

            self._insert_operation(
                cursor,
                transaction_id,
                operation_type,
                None,
                sequence_no,
                timestamp,
            )

            cursor.execute(
                """
                UPDATE transactions
                SET status = %s, end_time = %s
                WHERE transaction_id = %s AND status = %s
                """,
                (status, timestamp, transaction_id, "ACTIVE"),
            )

            if cursor.rowcount != 1:
                raise TransactionStateError(
                    f"Transaction {transaction_id} could not be finished"
                )

            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def _insert_operation(
        cursor,
        transaction_id,
        operation_type,
        data_item,
        sequence_no,
        timestamp,
    ):
        cursor.execute(
            """
            INSERT INTO transaction_operations
                (transaction_id, operation_type, data_item, sequence_no, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                transaction_id,
                operation_type,
                data_item,
                sequence_no,
                timestamp,
            ),
        )
