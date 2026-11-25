"""Ambiguous DBMS observations must not be assigned to an arbitrary query."""

from app.api.routes_correlation import auto_correlate
from app.models.auto_correlation import AutoCorrelationRequest


class FakeConnection:
    def rollback(self):
        raise AssertionError("read-only ambiguous correlation must not roll back")

    def close(self):
        pass


def test_auto_correlation_reports_ambiguous_query_candidates(monkeypatch):
    class FakeRepository:
        def __init__(self, connection):
            pass

        def observation(self, observation_id):
            return {"observation_id": observation_id}

        def matching_queries(self, observation, window_ms):
            return [{"query_id": 10}, {"query_id": 11}]

    # routes_correlation imports the class directly, so replace that binding.
    import app.api.routes_correlation as routes_module

    monkeypatch.setattr(routes_module, "AutoCorrelationRepository", FakeRepository)

    result = auto_correlate(AutoCorrelationRequest(observation_id=4), FakeConnection())

    assert result.matched_query_id is None
    assert result.result is None
    assert result.reason == (
        "Correlation is ambiguous: multiple query executions match "
        "the DBMS observation and time window"
    )
