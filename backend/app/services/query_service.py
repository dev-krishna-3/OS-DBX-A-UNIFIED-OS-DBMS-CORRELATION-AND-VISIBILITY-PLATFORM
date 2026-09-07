"""Service for creating query execution DBMS events."""

from app.models.query_executions import DBMSEvent, QueryExecutionRecord, QueryExecutionRequest
from app.repositories.query_repository import QueryRepository
from app.services.transaction_service import utc_now


class QueryService:
    def __init__(self, repository: QueryRepository) -> None:
        self.repository = repository

    def record_query(self, request: QueryExecutionRequest) -> QueryExecutionRecord:
        event = DBMSEvent(**request.model_dump(), timestamp=utc_now())
        query_id = self.repository.record_query(event)
        return QueryExecutionRecord(query_id=query_id, **event.model_dump())
