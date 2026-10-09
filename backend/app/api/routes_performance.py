"""Performance measurement APIs."""

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.database import get_connection
from app.models.performance import PerformanceRecord, PerformanceRecordCreate
from app.repositories.performance_repository import PerformanceRepository

router = APIRouter(prefix="/performance", tags=["performance"])


def get_performance_repository(connection=Depends(get_connection)):
    try:
        yield PerformanceRepository(connection)
    finally:
        connection.close()


@router.post("/records", response_model=PerformanceRecord, status_code=201)
def create_performance_record(
    request: PerformanceRecordCreate,
    repository: PerformanceRepository = Depends(get_performance_repository),
) -> PerformanceRecord:
    try:
        return repository.create(request)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/records", response_model=list[PerformanceRecord])
def list_performance_records(
    limit: int = Query(default=50, ge=1, le=500),
    trace_id: int | None = Query(default=None, gt=0),
    repository: PerformanceRepository = Depends(get_performance_repository),
) -> list[PerformanceRecord]:
    try:
        return repository.recent(limit, trace_id)
    except mysql.connector.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
