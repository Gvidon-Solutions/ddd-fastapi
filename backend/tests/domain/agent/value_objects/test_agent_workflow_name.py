"""AgentWorkflowName value object tests."""

import pytest

from app.domain.agent.value_objects import AgentWorkflowName


def test_agent_workflow_name_accepts_valid_value() -> None:
    # Arrange
    value = "agentic_requirements_review"

    # Act
    workflow_name = AgentWorkflowName(value)

    # Assert
    assert workflow_name.value == value
    assert str(workflow_name) == value


def test_agent_workflow_name_rejects_empty_value() -> None:
    # Arrange
    value = ""

    # Act / Assert
    with pytest.raises(ValueError, match="required"):
        AgentWorkflowName(value)


def test_agent_workflow_name_rejects_long_value() -> None:
    # Arrange
    value = "x" * 121

    # Act / Assert
    with pytest.raises(ValueError, match="120"):
        AgentWorkflowName(value)
