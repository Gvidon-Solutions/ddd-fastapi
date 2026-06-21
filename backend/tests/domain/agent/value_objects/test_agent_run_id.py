"""AgentRunId value object tests."""

from uuid import UUID

from app.domain.agent.value_objects import AgentRunId


def test_agent_run_id_generates_uuid() -> None:
    # Act
    agent_run_id = AgentRunId.generate()

    # Assert
    assert isinstance(agent_run_id.value, UUID)
    assert str(agent_run_id) == str(agent_run_id.value)
