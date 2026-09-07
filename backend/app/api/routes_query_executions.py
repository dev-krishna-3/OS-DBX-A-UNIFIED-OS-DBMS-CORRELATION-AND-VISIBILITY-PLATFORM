"""Query execution tracking API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.config.database import get_connection
from app.models.query_executions import QueryExecutionRecord, QueryExecutionRequest
from app.repositories.query_repository import QueryRepository, TransactionPIDMismatchError
from app.repositories.transaction_repository import TransactionNotFoundError, TransactionStateError
from app.services.query_service import QueryService

router = APIRouter(prefix="/query-executions", tags=["query-executions"])


def get_query_service(connection=Depends(get_connection)):
    try:
        yield QueryService(QueryRepository(connection))
    finally:
        connection.close()


def _query_error(error: Exception) -> HTTPException:
    if isinstance(error, TransactionNotFoundError):
        return HTTPException(status_code=404, detail="Transaction not found")
    return HTTPException(status_code=409, detail=str(error))


@router.post("", response_model=QueryExecutionRecord, status_code=201)
def record_query(
    request: QueryExecutionRequest,
    service: QueryService = Depends(get_query_service),
) -> QueryExecutionRecord:
    try:
        return service.record_query(request)
    except (TransactionNotFoundError, TransactionStateError, TransactionPIDMismatchError) as error:
        raise _query_error(error) from error
