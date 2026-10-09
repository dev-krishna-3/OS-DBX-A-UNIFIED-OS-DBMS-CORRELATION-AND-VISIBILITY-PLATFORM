"""DBMS schedule analysis API."""

from fastapi import APIRouter

from app.models.schedules import ScheduleAnalysisRequest, ScheduleAnalysisResult
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/analyze", response_model=ScheduleAnalysisResult)
def analyze_schedule(request: ScheduleAnalysisRequest) -> ScheduleAnalysisResult:
    return ScheduleService().analyze(request.operations)
