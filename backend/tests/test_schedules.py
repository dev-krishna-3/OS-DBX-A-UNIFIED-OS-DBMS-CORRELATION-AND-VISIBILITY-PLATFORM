from app.models.schedules import ScheduleOperation
from app.services.schedule_service import ScheduleService


def test_schedule_with_cycle_is_not_conflict_serializable():
    result = ScheduleService().analyze(
        [
            ScheduleOperation(transaction_id=1, operation="W", data_item="A"),
            ScheduleOperation(transaction_id=2, operation="R", data_item="A"),
            ScheduleOperation(transaction_id=2, operation="W", data_item="B"),
            ScheduleOperation(transaction_id=1, operation="R", data_item="B"),
        ]
    )

    assert not result.conflict_serializable
    assert result.precedence_graph == {"1": [2], "2": [1]}
    assert result.cycles == [[1, 2]]


def test_non_conflicting_schedule_is_serializable():
    result = ScheduleService().analyze(
        [
            ScheduleOperation(transaction_id=1, operation="R", data_item="A"),
            ScheduleOperation(transaction_id=2, operation="R", data_item="A"),
        ]
    )

    assert result.conflict_serializable
    assert result.precedence_graph == {}
