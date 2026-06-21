"""Taskiq configuration tests."""

from app.infrastructure.taskiq import (
    broker,
    enqueue_agent_workflow,
    run_agent_workflow_task,
)


def test_taskiq_infrastructure_is_importable() -> None:
    # Act & Assert
    assert broker is not None
    assert enqueue_agent_workflow is not None
    assert run_agent_workflow_task is not None
