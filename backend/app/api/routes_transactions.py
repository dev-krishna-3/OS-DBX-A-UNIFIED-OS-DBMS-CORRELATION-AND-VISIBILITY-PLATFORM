"""Transaction manager API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.config.database import get_connection
from app.models.transactions import BeginTransactionRequest, TransactionOperationRequest
from app.repositories.lock_repository import LockRepository
from app.repositories.transaction_repository import (
    TransactionNotFoundError,
    TransactionRepository,
    TransactionStateError,
)
from app.services.transaction_service import TransactionService
from app.services.lock_manager import LockManager

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_transaction_service(connection=Depends(get_connection)):
    try:
        yield TransactionService(
            TransactionRepository(connection),
            LockManager(LockRepository(connection)),
        )
    finally:
        connection.close()


def _state_error(error: Exception) -> HTTPException:
    if isinstance(error, TransactionNotFoundError):
        return HTTPException(status_code=404, detail="Transaction not found")
    if isinstance(error, TransactionStateError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, HTTPException):
        return error
    return HTTPException(status_code=500, detail=f"Transaction processing error: {error}")


@router.post("/begin", status_code=201)
def begin_transaction(request: BeginTransactionRequest, service=Depends(get_transaction_service)):
    try:
        transaction_id = service.begin(request.pid, request.isolation_level.value)
        return {"transaction_id": transaction_id, "status": "ACTIVE"}
    except Exception as error:
        raise _state_error(error) from error


@router.post("/{transaction_id}/read")
def read_operation(transaction_id: int, request: TransactionOperationRequest, service=Depends(get_transaction_service)):
    try:
        sequence_no = service.read(transaction_id, request.data_item)
        return {"transaction_id": transaction_id, "operation_type": "READ", "sequence_no": sequence_no}
    except (TransactionNotFoundError, TransactionStateError) as error:
        raise _state_error(error) from error


@router.post("/{transaction_id}/write")
def write_operation(transaction_id: int, request: TransactionOperationRequest, service=Depends(get_transaction_service)):
    try:
        sequence_no = service.write(transaction_id, request.data_item)
        return {"transaction_id": transaction_id, "operation_type": "WRITE", "sequence_no": sequence_no}
    except (TransactionNotFoundError, TransactionStateError) as error:
        raise _state_error(error) from error


@router.post("/{transaction_id}/commit")
def commit_transaction(transaction_id: int, service=Depends(get_transaction_service)):
    try:
        service.commit(transaction_id)
        return {"transaction_id": transaction_id, "status": "COMMITTED"}
    except (TransactionNotFoundError, TransactionStateError) as error:
        raise _state_error(error) from error


@router.post("/{transaction_id}/rollback")
def rollback_transaction(transaction_id: int, service=Depends(get_transaction_service)):
    try:
        service.rollback(transaction_id)
        return {"transaction_id": transaction_id, "status": "ROLLED_BACK"}
    except (TransactionNotFoundError, TransactionStateError) as error:
        raise _state_error(error) from error


@router.get("")
def list_transactions(limit: int = 30) -> list[dict]:
    """Return recent transactions with their PID, status, isolation level, and latest operation."""
    items: list[dict] = []
    try:
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT
                    t.transaction_id,
                    t.pid,
                    t.status,
                    t.isolation_level,
                    t.start_time,
                    t.end_time,
                    COUNT(op.operation_id) AS op_count,
                    MAX(op.operation_type) AS last_op_type,
                    MAX(op.data_item) AS last_data_item
                FROM transactions t
                LEFT JOIN transaction_operations op ON op.transaction_id = t.transaction_id
                GROUP BY t.transaction_id, t.pid, t.status, t.isolation_level, t.start_time, t.end_time
                ORDER BY (t.status = 'ACTIVE') DESC, t.transaction_id DESC
                LIMIT %s
                """,
                (max(1, min(limit, 100)),),
            )
            for row in cur.fetchall():
                items.append(
                    {
                        "transaction_id": row["transaction_id"],
                        "pid": row["pid"],
                        "status": row["status"],
                        "isolation_level": row.get("isolation_level") or "REPEATABLE_READ",
                        "start_time": row["start_time"].isoformat() if hasattr(row.get("start_time"), "isoformat") else str(row.get("start_time") or ""),
                        "end_time": row["end_time"].isoformat() if hasattr(row.get("end_time"), "isoformat") else None,
                        "op_count": int(row.get("op_count") or 0),
                        "last_op_type": row.get("last_op_type"),
                        "last_data_item": row.get("last_data_item"),
                    }
                )
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return items

