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
    return HTTPException(status_code=409, detail=str(error))


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
