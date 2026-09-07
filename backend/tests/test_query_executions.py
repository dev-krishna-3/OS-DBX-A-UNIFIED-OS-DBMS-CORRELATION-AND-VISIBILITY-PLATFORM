"""Tests for DBMS query execution tracking."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.query_executions import QueryExecutionRequest
from app.repositories.query_repository import (
    QueryRepository,
    TransactionPIDMismatchError,
)
from app.repositories.transaction_repository import TransactionNotFoundError
from app.services.query_service import QueryService


VALID_REQUEST = QueryExecutionRequest(
    transaction_id=12,
    pid=4211,
    query_type="SELECT",
    query_text="SELECT * FROM users",
    execution_time_ms=12.5,
    rows_affected=3,
    status="SUCCESS",
)


class FakeQueryRepository:
    def __init__(self, query_id=25):
        self.query_id = query_id
        self.events = []

    def record_query(self, event):
        self.events.append(event)
        return self.query_id


def test_valid_query_record_contains_execution_details():
    repository = FakeQueryRepository()
    record = QueryService(repository).record_query(VALID_REQUEST)

    assert record.query_id == 25
    assert record.transaction_id == 12
    assert record.pid == 4211
    assert record.query_type == "SELECT"
    assert record.query_text == "SELECT * FROM users"
    assert record.execution_time_ms == 12.5
    assert record.rows_affected == 3
    assert record.status == "SUCCESS"
    assert record.event_type == "QUERY_EXECUTION"


def test_query_is_associated_with_transaction_and_pid():
    repository = FakeQueryRepository()
    QueryService(repository).record_query(VALID_REQUEST)

    event = repository.events[0]
    assert event.transaction_id == VALID_REQUEST.transaction_id
    assert event.pid == VALID_REQUEST.pid


def test_query_timestamp_is_utc_without_timezone_for_mysql():
    repository = FakeQueryRepository()
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    record = QueryService(repository).record_query(VALID_REQUEST)
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert before <= record.timestamp <= after
    assert record.timestamp.tzinfo is None


def test_invalid_input_is_rejected():
    with pytest.raises(ValidationError):
        QueryExecutionRequest(
            transaction_id=0,
            pid=4211,
            query_type="SELECT",
            query_text="SELECT 1",
            execution_time_ms=-1,
            rows_affected=-1,
            status="",
        )


class FakeCursor:
    def __init__(self, transaction=None):
        self.transaction = transaction
        self.calls = []
        self.lastrowid = 31

    def execute(self, query, parameters):
        self.calls.append((query, parameters))

    def fetchone(self):
        return self.transaction

    def close(self):
        pass


class FakeConnection:
    def __init__(self, transaction=None):
        self.cursor_instance = FakeCursor(transaction)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        assert dictionary is True
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_repository_writes_query_with_parameterized_values():
    connection = FakeConnection({"pid": 4211, "status": "ACTIVE"})
    event = QueryService(FakeQueryRepository()).record_query(VALID_REQUEST)
    query_id = QueryRepository(connection).record_query(event)

    assert query_id == 31
    insert_query, values = connection.cursor_instance.calls[1]
    assert "INSERT INTO query_executions" in insert_query
    assert "%s" in insert_query
    assert values == (
        12,
        4211,
        "SELECT",
        "SELECT * FROM users",
        12.5,
        3,
        "SUCCESS",
        event.timestamp,
    )
    assert connection.commits == 1


def test_repository_rejects_invalid_transaction():
    connection = FakeConnection(None)
    event = QueryService(FakeQueryRepository()).record_query(VALID_REQUEST)

    with pytest.raises(TransactionNotFoundError):
        QueryRepository(connection).record_query(event)

    assert len(connection.cursor_instance.calls) == 1
    assert connection.rollbacks == 1


def test_repository_rejects_pid_mismatch():
    connection = FakeConnection({"pid": 9999, "status": "ACTIVE"})
    event = QueryService(FakeQueryRepository()).record_query(VALID_REQUEST)

    with pytest.raises(TransactionPIDMismatchError):
        QueryRepository(connection).record_query(event)

    assert connection.rollbacks == 1
