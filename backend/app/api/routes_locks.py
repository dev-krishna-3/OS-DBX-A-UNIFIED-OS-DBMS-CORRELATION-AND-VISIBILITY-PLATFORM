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
    return HTTPException(status_code=409, detail=str(error))


@router.post("", response_model=LockRecord, status_code=201)
def acquire_lock(
    request: LockRequest,
    manager: LockManager = Depends(get_lock_manager),
) -> LockRecord:
    try:
        return manager.acquire(request)
    except (TransactionNotFoundError, TransactionStateError) as error:
        raise _lock_error(error) from error
