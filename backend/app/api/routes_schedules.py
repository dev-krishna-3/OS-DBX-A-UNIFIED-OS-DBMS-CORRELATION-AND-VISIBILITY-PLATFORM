"""DBMS schedule analysis API."""

from fastapi import APIRouter

from app.models.schedules import ScheduleAnalysisRequest, ScheduleAnalysisResult
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/analyze", response_model=ScheduleAnalysisResult)
def analyze_schedule(request: ScheduleAnalysisRequest) -> ScheduleAnalysisResult:
    result = ScheduleService().analyze(request.operations)
    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schedules (description, is_serializable, created_at) VALUES (%s, %s, NOW())",
                (f"Schedule with {len(request.operations)} operations", result.conflict_serializable)
            )
            sched_id = cur.lastrowid
            for idx, op in enumerate(request.operations, 1):
                cur.execute(
                    "INSERT INTO schedule_operations (schedule_id, operation_id, position) VALUES (%s, %s, %s)",
                    (sched_id, op.transaction_id, idx)
                )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return result

