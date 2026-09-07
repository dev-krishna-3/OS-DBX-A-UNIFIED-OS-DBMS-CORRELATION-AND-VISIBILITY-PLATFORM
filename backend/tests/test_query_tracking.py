"""Unit tests for DBMS query tracking using fakes instead of MySQL."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.query_executions import QueryExecutionRequest
from app.repositories.query_repository import QueryRepository
from app.repositories.transaction_repository import (
    TransactionNotFoundError,
    TransactionPIDMismatchError,
)
from app.services.query_service import QueryService


FIXED_TIMESTAMP = datetime(2026, 9, 7, 8, 30, 0)


def request(**overrides: object) -> QueryExecutionRequest:
    values = {
        "transaction_id": 12,
        "pid": 4211,
        "query_type": "SELECT",
        "query_text": "SELECT * FROM users",
        "execution_time_ms": 12.5,
        "rows_affected": 3,
        "status": "SUCCESS",
        "timestamp": FIXED_TIMESTAMP,
    }
    values.update(overrides)
    return QueryExecutionRequest(**values)


class FakeQueryRepository:
    def __init__(self, query_id: int = 25) -> None:
        self.query_id = query_id
        self.events = []

    def record_query(self, event):
        self.events.append(event)
        return self.query_id


class FakeCursor:
    def __init__(self, transaction=None, *, error: Exception | None = None) -> None:
        self.transaction = transaction
        self.error = error
        self.calls = []
        self.lastrowid = 31

    def execute(self, query, parameters):
        self.calls.append((query, parameters))
        if self.error is not None:
            raise self.error

    def fetchone(self):
        return self.transaction

    def close(self):
        pass


class FakeConnection:
    def __init__(self, transaction=None, *, error: Exception | None = None) -> None:
        self.cursor_instance = FakeCursor(transaction, error=error)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *, dictionary: bool):
        assert dictionary is True
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_successful_query_recording_persists_all_metadata():
    repository = FakeQueryRepository()

    record = QueryService(repository).record_query(request())

    assert record.query_id == 25
    assert record.event_type == "QUERY_EXECUTION"
    assert record.model_dump(exclude={"event_type", "query_id"}) == {
        "transaction_id": 12,
        "pid": 4211,
        "query_type": "SELECT",
        "query_text": "SELECT * FROM users",
        "execution_time_ms": 12.5,
        "rows_affected": 3,
        "status": "SUCCESS",
        "timestamp": FIXED_TIMESTAMP,
    }


def test_transaction_id_and_pid_are_associated():
    repository = FakeQueryRepository()

    QueryService(repository).record_query(request())

    assert repository.events[0].transaction_id == 12
    assert repository.events[0].pid == 4211


def test_timestamp_is_deterministic_and_mysql_compatible():
    repository = FakeQueryRepository()
    aware_timestamp = datetime(2026, 9, 7, 8, 30, tzinfo=timezone.utc)

    record = QueryService(repository).record_query(request(timestamp=aware_timestamp))

    assert record.timestamp == FIXED_TIMESTAMP
    assert record.timestamp.tzinfo is None


def test_missing_timestamp_is_generated_as_utc_naive():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    record = QueryService(FakeQueryRepository()).record_query(
        request(timestamp=None)
    )
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert before <= record.timestamp <= after
    assert record.timestamp.tzinfo is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("transaction_id", 0),
        ("pid", 0),
        ("execution_time_ms", -1),
        ("rows_affected", -1),
        ("status", " "),
        ("query_text", ""),
    ],
)
def test_invalid_input_is_rejected(field, value):
    with pytest.raises(ValidationError):
        request(**{field: value})


def test_repository_uses_parameterized_sql_and_commits():
    connection = FakeConnection({"pid": 4211, "status": "ACTIVE"})
    event = QueryService(FakeQueryRepository()).record_query(request())

    query_id = QueryRepository(connection).record_query(event)

    assert query_id == 31
    assert len(connection.cursor_instance.calls) == 2
    insert_query, values = connection.cursor_instance.calls[1]
    assert "INSERT INTO query_executions" in insert_query
    assert values == (
        12,
        4211,
        "SELECT",
        "SELECT * FROM users",
        12.5,
        3,
        "SUCCESS",
        FIXED_TIMESTAMP,
    )
    assert "%s" in insert_query
    assert connection.commits == 1


def test_repository_rolls_back_when_transaction_is_missing():
    connection = FakeConnection(None)
    event = QueryService(FakeQueryRepository()).record_query(request())

    with pytest.raises(TransactionNotFoundError):
        QueryRepository(connection).record_query(event)

    assert len(connection.cursor_instance.calls) == 1
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_repository_rolls_back_when_pid_does_not_match_transaction():
    connection = FakeConnection({"pid": 9999, "status": "ACTIVE"})
    event = QueryService(FakeQueryRepository()).record_query(request())

    with pytest.raises(TransactionPIDMismatchError):
        QueryRepository(connection).record_query(event)

    assert len(connection.cursor_instance.calls) == 1
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_repository_rolls_back_database_errors():
    connection = FakeConnection(
        {"pid": 4211, "status": "ACTIVE"},
        error=RuntimeError("database unavailable"),
    )
    event = QueryService(FakeQueryRepository()).record_query(request())

    with pytest.raises(RuntimeError, match="database unavailable"):
        QueryRepository(connection).record_query(event)

    assert connection.commits == 0
    assert connection.rollbacks == 1
