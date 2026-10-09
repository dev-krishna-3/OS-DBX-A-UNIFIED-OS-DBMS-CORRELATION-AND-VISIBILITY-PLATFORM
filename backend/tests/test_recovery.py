from app.models.recovery import RecoveryLogEntry
from app.services.recovery_service import RecoveryService


def test_redo_committed_updates_and_undoes_loser_transaction():
    result = RecoveryService().recover(
        {"balance": "100"},
        [
            RecoveryLogEntry(
                sequence=1,
                transaction_id=10,
                log_type="UPDATE",
                data_item="balance",
                old_value="100",
                new_value="150",
            ),
            RecoveryLogEntry(sequence=2, transaction_id=10, log_type="COMMIT"),
            RecoveryLogEntry(
                sequence=3,
                transaction_id=11,
                log_type="UPDATE",
                data_item="balance",
                old_value="150",
                new_value="125",
            ),
        ],
    )

    assert result.final_state == {"balance": "150"}
    assert result.committed_transactions == [10]
    assert result.undone_transactions == [11]
