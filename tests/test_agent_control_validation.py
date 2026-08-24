import pytest

from tools.validate_agent_control import (
    main,
    validate_implemented_fixtures_materialized,
    validate_task_statuses,
)


def test_agent_control_validation():
    main()


def test_backlog_statuses_are_accepted_not_only_implemented():
    tasks = [
        {"ticket_id": "X-1", "status": "planned"},
        {"ticket_id": "X-2", "status": "in_progress"},
        {"ticket_id": "X-3", "status": "blocked"},
        {"ticket_id": "X-4", "status": "implemented"},
    ]
    validate_task_statuses(tasks)  # must not raise


def test_unrecognized_status_still_rejected():
    tasks = [{"ticket_id": "X-1", "status": "definitely_done_trust_me"}]
    with pytest.raises(AssertionError, match="unrecognized status"):
        validate_task_statuses(tasks)


def test_backlog_task_may_reference_unmaterialized_fixture():
    tasks = [
        {"ticket_id": "X-1", "status": "in_progress", "required_fixtures": ["not_built_yet"]},
    ]
    validate_implemented_fixtures_materialized(tasks, fixture_ids=set())  # must not raise


def test_implemented_task_must_reference_materialized_fixture():
    tasks = [
        {"ticket_id": "X-1", "status": "implemented", "required_fixtures": ["not_built_yet"]},
    ]
    with pytest.raises(AssertionError, match="unmaterialized fixtures"):
        validate_implemented_fixtures_materialized(tasks, fixture_ids=set())


def test_implemented_task_passes_when_fixture_is_materialized():
    tasks = [
        {"ticket_id": "X-1", "status": "implemented", "required_fixtures": ["real_fixture"]},
    ]
    validate_implemented_fixtures_materialized(tasks, fixture_ids={"real_fixture"})  # must not raise
