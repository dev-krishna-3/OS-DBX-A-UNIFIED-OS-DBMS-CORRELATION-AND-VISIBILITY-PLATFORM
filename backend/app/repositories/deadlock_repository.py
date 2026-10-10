"""Database access for live lock snapshots and detected deadlock incidents."""

from datetime import datetime, timezone

from app.models.deadlocks import IncidentRecord, LockSnapshot


class DeadlockRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def active_locks(self) -> list[LockSnapshot]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT transaction_id, data_item, lock_type, status
                FROM locks
                WHERE status IN (%s, %s)
                ORDER BY transaction_id, lock_id
                """,
                ("HELD", "WAITING"),
            )
            return [LockSnapshot(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def record_deadlock(self, cycles: list[list[int]], graph: dict[str, list[int]]) -> int:
        cursor = self.connection.cursor()
        try:
            description = f"Wait-for cycle(s): {cycles}; graph: {graph}"
            # Repeated polling should reuse the open incident for the same
            # current wait-for graph instead of recording duplicates.
            cursor.execute(
                """
                SELECT incident_id
                FROM incidents
                WHERE incident_type = %s AND resolved = %s AND description = %s
                ORDER BY incident_id DESC
                LIMIT 1
                """,
                ("DEADLOCK", False, description),
            )
            existing = cursor.fetchone()
            if existing:
                self.connection.rollback()
                incident_id = (
                    existing["incident_id"]
                    if isinstance(existing, dict)
                    else existing[0]
                )
                return int(incident_id)

            # Collect all transaction IDs involved in all deadlock cycles
            all_cycle_txs = list({t for sub in cycles for t in sub}) if cycles else []
            traces_map = {}
            lock_ids = []
            query_ids = []
            pids = []
            os_events = []
            trace_id = None

            if all_cycle_txs:
                format_strings = ','.join(['%s'] * len(all_cycle_txs))
                
                # 1. Look up cross_layer_traces for all transactions involved in the cycle
                cursor.execute(
                    f"""
                    SELECT trace_id, transaction_id, pid, summary
                    FROM cross_layer_traces
                    WHERE transaction_id IN ({format_strings})
                    ORDER BY started_at DESC
                    """,
                    tuple(all_cycle_txs)
                )
                trace_rows = cursor.fetchall()
                for tr in trace_rows:
                    t_id = tr['trace_id'] if isinstance(tr, dict) else tr[0]
                    tx_id = tr['transaction_id'] if isinstance(tr, dict) else tr[1]
                    p_id = tr['pid'] if isinstance(tr, dict) else tr[2]
                    if tx_id not in traces_map:
                        traces_map[tx_id] = t_id
                    if p_id and p_id not in pids:
                        pids.append(p_id)
                
                # Pick the most recent trace_id as primary link
                if trace_rows:
                    first_row = trace_rows[0]
                    trace_id = first_row['trace_id'] if isinstance(first_row, dict) else first_row[0]

                # 2. Look up active locks for all involved transactions
                try:
                    cursor.execute(
                        f"""
                        SELECT lock_id, transaction_id, data_item, lock_type, status
                        FROM locks
                        WHERE transaction_id IN ({format_strings}) AND status IN ('HELD', 'WAITING')
                        ORDER BY lock_id
                        """,
                        tuple(all_cycle_txs)
                    )
                    lock_rows = cursor.fetchall()
                    for lr in lock_rows:
                        l_id = lr['lock_id'] if isinstance(lr, dict) else lr[0]
                        lock_ids.append(l_id)
                except Exception:
                    pass

                # 3. Look up query executions for involved transactions
                try:
                    cursor.execute(
                        f"""
                        SELECT query_id, transaction_id, query_type, pid
                        FROM query_executions
                        WHERE transaction_id IN ({format_strings})
                        ORDER BY query_id DESC LIMIT 10
                        """,
                        tuple(all_cycle_txs)
                    )
                    q_rows = cursor.fetchall()
                    for qr in q_rows:
                        qid = qr['query_id'] if isinstance(qr, dict) else qr[0]
                        qpid = qr['pid'] if isinstance(qr, dict) else qr[3]
                        query_ids.append(qid)
                        if qpid and qpid not in pids:
                            pids.append(qpid)
                except Exception:
                    pass

                # 4. If we have PIDs, look up recent OS events
                if pids:
                    try:
                        pid_placeholders = ','.join(['%s'] * len(pids))
                        cursor.execute(
                            f"""
                            SELECT event_id, pid, event_type, timestamp
                            FROM os_events
                            WHERE pid IN ({pid_placeholders})
                            ORDER BY timestamp DESC LIMIT 10
                            """,
                            tuple(pids)
                        )
                        ev_rows = cursor.fetchall()
                        for er in ev_rows:
                            ev_id = er['event_id'] if isinstance(er, dict) else er[0]
                            os_events.append(ev_id)
                    except Exception:
                        pass

            import json
            
            # Serialize structured evidence containing both sides of the deadlock cycle
            evidence_payload = json.dumps({
                "transaction_ids": all_cycle_txs,
                "wait_for_graph": graph,
                "transaction_traces": traces_map,
                "lock_ids": lock_ids,
                "query_ids": query_ids,
                "pids": pids,
                "os_events": os_events
            })
            
            cursor.execute(
                """
                INSERT INTO incidents
                    (trace_id, incident_type, description, severity, evidence, detected_at, resolved)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    trace_id,
                    "DEADLOCK",
                    description,
                    "HIGH",
                    evidence_payload,
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    False,
                ),
            )
            incident_id = int(cursor.lastrowid)
            self.connection.commit()
            return incident_id
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def recent_incidents(self, limit: int = 50) -> list[IncidentRecord]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT incident_id, trace_id, incident_type, description,
                       detected_at, resolved
                FROM incidents
                ORDER BY detected_at DESC, incident_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [IncidentRecord(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()
