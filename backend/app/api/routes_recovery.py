"""Recovery experiment API."""

from fastapi import APIRouter

from app.models.recovery import RecoveryRequest, RecoveryResult
from app.services.recovery_service import RecoveryService

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post("/recover", response_model=RecoveryResult)
def recover(request: RecoveryRequest) -> RecoveryResult:
    result = RecoveryService().recover(request.initial_state, request.logs)
    try:
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            for entry in request.logs:
                cur.execute(
                    """
                    INSERT INTO recovery_logs (transaction_id, log_type, data_item, old_value, new_value, timestamp)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (entry.transaction_id, entry.log_type, entry.data_item, entry.old_value, entry.new_value)
                )
            cur.execute(
                "INSERT INTO checkpoints (timestamp, active_transactions) VALUES (NOW(), %s)",
                (str(result.undone_transactions),)
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return result

