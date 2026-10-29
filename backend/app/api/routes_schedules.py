"""DBMS schedule analysis API."""

from fastapi import APIRouter

from app.models.schedules import ScheduleAnalysisRequest, ScheduleAnalysisResult
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/analyze", response_model=ScheduleAnalysisResult)
def analyze_schedule(request: ScheduleAnalysisRequest) -> ScheduleAnalysisResult:
    result = ScheduleService().analyze(request.operations)
    try:
        import os
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schedules (description, is_serializable, created_at) VALUES (%s, %s, NOW())",
                (f"Schedule with {len(request.operations)} operations", result.conflict_serializable)
            )
            sched_id = cur.lastrowid
            cur.execute(
                "INSERT IGNORE INTO processes (pid, name, state, start_time) VALUES (%s, 'schedule_analyzer', 'RUNNING', NOW())",
                (os.getpid(),),
            )
            for idx, op in enumerate(request.operations, 1):
                cur.execute(
                    "INSERT IGNORE INTO transactions (transaction_id, pid, status, start_time, isolation_level) VALUES (%s, %s, 'COMMITTED', NOW(), 'READ_COMMITTED')",
                    (op.transaction_id, os.getpid()),
                )
                op_type = "READ" if str(getattr(op.operation, "value", op.operation)).upper().startswith("R") else "WRITE"
                cur.execute(
                    """
                    INSERT INTO transaction_operations (transaction_id, operation_type, data_item, sequence_no, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (op.transaction_id, op_type, op.data_item, idx),
                )
                op_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO schedule_operations (schedule_id, operation_id, position) VALUES (%s, %s, %s)",
                    (sched_id, op_id, idx)
                )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return result


@router.get("/history")
def list_schedules_history(limit: int = 25) -> dict:
    """Return stored schedules and schedule_operations."""
    from app.config.database import get_connection
    data = {"schedules": [], "schedule_operations": []}
    try:
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM schedules ORDER BY schedule_id DESC LIMIT %s", (limit,))
            data["schedules"] = cur.fetchall()
            cur.execute("SELECT * FROM schedule_operations ORDER BY id DESC LIMIT %s", (limit,))
            data["schedule_operations"] = cur.fetchall()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return data


