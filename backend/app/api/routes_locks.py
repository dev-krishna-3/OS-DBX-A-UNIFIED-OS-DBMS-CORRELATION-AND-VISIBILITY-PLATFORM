"""Lock acquisition API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.config.database import get_connection
from app.models.locks import LockRecord, LockRequest
from app.repositories.transaction_repository import TransactionNotFoundError, TransactionStateError
from app.services.lock_manager import LockManager
from app.repositories.lock_repository import LockRepository

router = APIRouter(prefix="/locks", tags=["locks"])


def get_lock_manager(connection=Depends(get_connection)):
    try:
        yield LockManager(LockRepository(connection))
    finally:
        connection.close()


def _lock_error(error: Exception) -> HTTPException:
    if isinstance(error, TransactionNotFoundError):
        return HTTPException(status_code=404, detail="Transaction not found")
    if isinstance(error, TransactionStateError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, HTTPException):
        return error
    return HTTPException(status_code=500, detail=f"Lock service error: {error}")


@router.post("", response_model=LockRecord, status_code=201)
def acquire_lock(
    request: LockRequest,
    manager: LockManager = Depends(get_lock_manager),
) -> LockRecord:
    try:
        return manager.acquire(request)
    except (TransactionNotFoundError, TransactionStateError) as error:
        raise _lock_error(error) from error


@router.get("")
def list_locks(limit: int = 40) -> list[dict]:
    """Return active (HELD/WAITING) and recent locks from MySQL."""
    locks_out: list[dict] = []
    try:
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT lock_id, transaction_id, data_item, lock_type, status, acquired_at, released_at
                FROM locks
                ORDER BY (status IN ('HELD', 'WAITING')) DESC, lock_id DESC
                LIMIT %s
                """,
                (max(1, min(limit, 100)),),
            )
            for row in cur.fetchall():
                locks_out.append(
                    {
                        "lock_id": row["lock_id"],
                        "transaction_id": row["transaction_id"],
                        "data_item": row["data_item"],
                        "lock_type": row["lock_type"],
                        "status": row["status"],
                        "acquired_at": row["acquired_at"].isoformat() if hasattr(row.get("acquired_at"), "isoformat") else None,
                        "released_at": row["released_at"].isoformat() if hasattr(row.get("released_at"), "isoformat") else None,
                    }
                )
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return locks_out

