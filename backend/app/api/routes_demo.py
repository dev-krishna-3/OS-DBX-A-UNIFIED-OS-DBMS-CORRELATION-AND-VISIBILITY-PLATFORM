"""Self-contained demonstration routes for the correlation engine."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.correlation import CorrelationInput
from app.models.demo import CorrelationDemoResponse, DemoCheck
from app.services.correlation_service import CorrelationService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/correlation", response_model=CorrelationDemoResponse)
def run_correlation_demo() -> CorrelationDemoResponse:
    """Run the real correlation service against a known-good local fixture.

    This endpoint deliberately has no database dependency. It proves that the
    correlation engine can normalize events, validate shared identity, create
    a trace, and produce a deterministic causal sequence from the running API.
    The database-backed routes remain available separately for integration
    testing.
    """

    generated_at = datetime.now(timezone.utc)
    events = [
        CorrelationInput(
            os_event_id=1001,
            pid=4211,
            transaction_id=12,
            query_id=25,
            timestamp=generated_at,
            event_type="process_created",
            source="demo_os_collector",
        ),
        CorrelationInput(
            os_event_id=1002,
            pid=4211,
            transaction_id=12,
            query_id=25,
            timestamp=generated_at,
            event_type="transaction_started",
            source="demo_transaction_tracker",
        ),
        CorrelationInput(
            os_event_id=1003,
            pid=4211,
            transaction_id=12,
            query_id=25,
            timestamp=generated_at,
            event_type="query_executed",
            source="demo_dbms_tracker",
        ),
    ]
    result = CorrelationService().correlate(events)

    checks = [
        DemoCheck(
            name="trace_created",
            passed=result.trace is not None,
            detail="A cross-layer trace was created.",
        ),
        DemoCheck(
            name="all_events_correlated",
            passed=len(result.correlations) == len(events),
            detail=f"{len(result.correlations)} of {len(events)} events were correlated.",
        ),
        DemoCheck(
            name="causal_order_is_deterministic",
            passed=[item.os_event_id for item in result.causal_sequence]
            == [1001, 1002, 1003],
            detail="Events are ordered by timestamp and OS event ID.",
        ),
        DemoCheck(
            name="identity_is_consistent",
            passed=(
                result.trace is not None
                and result.trace.pid == 4211
                and result.trace.transaction_id == 12
                and all(item.query_id == 25 for item in result.correlations)
            ),
            detail="PID, transaction ID, and query ID agree across the trace.",
        ),
    ]

    return CorrelationDemoResponse(
        demo="deterministic_cross_layer_correlation",
        status="PASS" if all(check.passed for check in checks) else "FAIL",
        generated_at=generated_at,
        input_events=events,
        result=result,
        checks=checks,
    )
