"""Parameterized MySQL persistence for Strict 2PL locks."""

from datetime import datetime

from app.models.locks import LockRequest, LockStatus, LockType
from app.repositories.transaction_repository import (
    TransactionNotFoundError,
    TransactionStateError,
)


class LockRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def acquire(self, request: LockRequest, timestamp: datetime) -> dict:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT status
                FROM transactions
                WHERE transaction_id = %s
                FOR UPDATE
                """,
                (request.transaction_id,),
            )
            transaction = cursor.fetchone()
            if transaction is None:
                raise TransactionNotFoundError(request.transaction_id)
            if transaction["status"] != "ACTIVE":
                raise TransactionStateError(
                    f"Transaction {request.transaction_id} is {transaction['status']}, not ACTIVE"
                )

            cursor.execute(
                """
                SELECT lock_id, transaction_id, data_item, lock_type,
                       status, acquired_at, released_at
                FROM locks
                WHERE data_item = %s AND status = %s
                FOR UPDATE
                """,
                (request.data_item, LockStatus.HELD.value),
            )
            held_locks = cursor.fetchall()
            own_lock = next(
                (lock for lock in held_locks if lock["transaction_id"] == request.transaction_id),
                None,
            )
            other_locks = [
                lock for lock in held_locks if lock["transaction_id"] != request.transaction_id
            ]

            conflict = request.lock_type == LockType.EXCLUSIVE and bool(other_locks)
            conflict = conflict or (
                request.lock_type == LockType.SHARED
                and any(lock["lock_type"] == LockType.EXCLUSIVE.value for lock in other_locks)
            )
            if conflict:
                cursor.execute(
                    """
                    INSERT INTO locks
                        (transaction_id, data_item, lock_type, status, acquired_at, released_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.transaction_id,
                        request.data_item,
                        request.lock_type.value,
                        LockStatus.WAITING.value,
                        None,
                        None,
                    ),
                )
                result = {
                    "lock_id": cursor.lastrowid,
                    "transaction_id": request.transaction_id,
                    "data_item": request.data_item,
                    "lock_type": request.lock_type.value,
                    "status": LockStatus.WAITING.value,
                    "acquired_at": None,
                    "released_at": None,
                }
            elif own_lock is not None:
                if (
                    own_lock["lock_type"] == LockType.SHARED.value
                    and request.lock_type == LockType.EXCLUSIVE
                ):
                    cursor.execute(
                        """
                        UPDATE locks
                        SET lock_type = %s
                        WHERE lock_id = %s AND status = %s
                        """,
                        (
                            LockType.EXCLUSIVE.value,
                            own_lock["lock_id"],
                            LockStatus.HELD.value,
                        ),
                    )
                    own_lock["lock_type"] = LockType.EXCLUSIVE.value
                result = own_lock
            else:
                cursor.execute(
                    """
                    INSERT INTO locks
                        (transaction_id, data_item, lock_type, status, acquired_at, released_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.transaction_id,
                        request.data_item,
                        request.lock_type.value,
                        LockStatus.HELD.value,
                        timestamp,
                        None,
                    ),
                )
                result = {
                    "lock_id": cursor.lastrowid,
                    "transaction_id": request.transaction_id,
                    "data_item": request.data_item,
                    "lock_type": request.lock_type.value,
                    "status": LockStatus.HELD.value,
                    "acquired_at": timestamp,
                    "released_at": None,
                }

            self.connection.commit()
            return result
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def release_all(self, transaction_id: int, timestamp: datetime) -> int:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE locks
                SET status = %s, released_at = %s
                WHERE transaction_id = %s AND status IN (%s, %s)
                """,
                (
                    LockStatus.RELEASED.value,
                    timestamp,
                    transaction_id,
                    LockStatus.HELD.value,
                    LockStatus.WAITING.value,
                ),
            )
            released_count = cursor.rowcount
            self.connection.commit()
            return released_count
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()
