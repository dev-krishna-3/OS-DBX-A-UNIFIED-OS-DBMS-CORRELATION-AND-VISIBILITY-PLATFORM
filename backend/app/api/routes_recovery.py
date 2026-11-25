"""Recovery experiment API."""

from fastapi import APIRouter

from app.models.recovery import RecoveryRequest, RecoveryResult
from app.services.recovery_service import RecoveryService

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post("/recover", response_model=RecoveryResult)
def recover(request: RecoveryRequest) -> RecoveryResult:
    result = RecoveryService().recover(request.initial_state, request.logs)
    try:
        import os
        from app.config.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT IGNORE INTO processes (pid, name, state, start_time) VALUES (%s, 'recovery_engine', 'RUNNING', NOW())",
                (os.getpid(),),
            )
            for entry in request.logs:
                cur.execute(
                    "INSERT IGNORE INTO transactions (transaction_id, pid, status, start_time, isolation_level) VALUES (%s, %s, 'COMMITTED', NOW(), 'READ_COMMITTED')",
                    (entry.transaction_id, os.getpid()),
                )
                l_type = entry.log_type.value if hasattr(entry.log_type, "value") else str(entry.log_type)
                cur.execute(
                    """
                    INSERT INTO recovery_logs (transaction_id, log_type, data_item, old_value, new_value, timestamp)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        entry.transaction_id,
                        l_type,
                        entry.data_item,
                        str(entry.old_value) if entry.old_value is not None else None,
                        str(entry.new_value) if entry.new_value is not None else None,
                    )
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


@router.get("/history")
def list_recovery_history(limit: int = 25) -> dict:
    """Return stored recovery_logs and checkpoints."""
    from app.config.database import get_connection
    data = {"recovery_logs": [], "checkpoints": []}
    try:
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM recovery_logs ORDER BY log_id DESC LIMIT %s", (limit,))
            data["recovery_logs"] = cur.fetchall()
            cur.execute("SELECT * FROM checkpoints ORDER BY checkpoint_id DESC LIMIT %s", (limit,))
            data["checkpoints"] = cur.fetchall()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    return data


