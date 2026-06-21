"""AgentRun entity tests."""

from app.domain.agent.entities import AgentRun
from app.domain.agent.value_objects import (
    AgentPrompt,
    AgentRunStatus,
    AgentWorkflowName,
)
from app.domain.user.value_objects import UserId


def test_agent_run_create_starts_queued() -> None:
    # Arrange
    workflow_name = AgentWorkflowName("agentic_requirements_review")
    prompt = AgentPrompt("Review the requirements")

    # Act
    agent_run = AgentRun.create(workflow_name, prompt)

    # Assert
    assert agent_run.workflow_name == workflow_name
    assert agent_run.input_prompt == prompt
    assert agent_run.status == AgentRunStatus.QUEUED


def test_agent_run_create_stores_creator() -> None:
    # Arrange
    created_by_user_id = UserId.generate()

    # Act
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_architecture_review"),
        AgentPrompt("Review architecture"),
        created_by_user_id,
    )

    # Assert
    assert agent_run.created_by_user_id == created_by_user_id


def test_agent_run_equality_uses_identity() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("codex_implementation"),
        AgentPrompt("Implement feature"),
    )
    same_id = AgentRun(
        id=agent_run.id,
        workflow_name=AgentWorkflowName("agentic_requirements_review"),
        input_prompt=AgentPrompt("Different prompt"),
    )

    # Act
    runs_are_equal = agent_run == same_id

    # Assert
    assert runs_are_equal
    assert hash(agent_run) == hash(same_id)


def test_agent_run_start_marks_run_running() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
    )

    # Act
    agent_run.start()

    # Assert
    assert agent_run.status == AgentRunStatus.RUNNING
    assert agent_run.started_at is not None


def test_agent_run_complete_marks_run_succeeded() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
    )

    # Act
    agent_run.complete("done")

    # Assert
    assert agent_run.status == AgentRunStatus.SUCCEEDED
    assert agent_run.result == "done"
    assert agent_run.error_message is None
    assert agent_run.finished_at is not None


def test_agent_run_fail_marks_run_failed() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
    )

    # Act
    agent_run.fail("boom")

    # Assert
    assert agent_run.status == AgentRunStatus.FAILED
    assert agent_run.error_message == "boom"
    assert agent_run.finished_at is not None


def test_agent_run_cancel_marks_run_cancelled() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
    )

    # Act
    agent_run.cancel()

    # Assert
    assert agent_run.status == AgentRunStatus.CANCELLED
    assert agent_run.finished_at is not None
