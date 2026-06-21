"""AgentPrompt value object tests."""

import pytest

from app.domain.agent.value_objects import AgentPrompt


def test_agent_prompt_accepts_valid_value() -> None:
    # Arrange
    value = "Review this backend design"

    # Act
    prompt = AgentPrompt(value)

    # Assert
    assert prompt.value == value
    assert str(prompt) == value


def test_agent_prompt_rejects_empty_value() -> None:
    # Arrange
    value = ""

    # Act / Assert
    with pytest.raises(ValueError, match="required"):
        AgentPrompt(value)


def test_agent_prompt_rejects_long_value() -> None:
    # Arrange
    value = "x" * 20001

    # Act / Assert
    with pytest.raises(ValueError, match="20000"):
        AgentPrompt(value)
