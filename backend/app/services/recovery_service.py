"""A small, explainable REDO/UNDO recovery engine for DBMS experiments."""

from app.models.recovery import RecoveryLogEntry, RecoveryResult


class RecoveryService:
    """Redo logged updates, then undo updates belonging to loser transactions."""

    def recover(
        self,
        initial_state: dict[str, str],
        logs: list[RecoveryLogEntry],
    ) -> RecoveryResult:
        ordered = sorted(logs, key=lambda entry: entry.sequence)
        committed = {
            entry.transaction_id
            for entry in ordered
            if entry.log_type.upper() == "COMMIT"
        }
        updates = [
            entry
            for entry in ordered
            if entry.log_type.upper() in {"UPDATE", "WRITE"}
            and entry.data_item is not None
        ]
        state = dict(initial_state)

        # REDO: replay every durable update in WAL order.
        for entry in updates:
            if entry.new_value is not None:
                state[entry.data_item] = entry.new_value

        losers = {entry.transaction_id for entry in updates} - committed
        # UNDO: reverse loser updates, restoring each old value.
        for entry in reversed(updates):
            if entry.transaction_id in losers and entry.old_value is not None:
                state[entry.data_item] = entry.old_value

        return RecoveryResult(
            final_state=state,
            redone_transactions=sorted({entry.transaction_id for entry in updates}),
            undone_transactions=sorted(losers),
            committed_transactions=sorted(committed),
        )
