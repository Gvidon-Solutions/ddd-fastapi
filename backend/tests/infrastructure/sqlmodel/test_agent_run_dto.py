"""AgentRunDTO tests."""

from app.domain.agent.entities import AgentRun
from app.domain.agent.value_objects import (
    AgentPrompt,
    AgentRunStatus,
    AgentWorkflowName,
)
from app.domain.user.value_objects import UserId
from app.infrastructure.sqlmodel.agent import AgentRunDTO


def test_agent_run_dto_uses_agent_run_table_name() -> None:
    # Act
    table_name = AgentRunDTO.__tablename__

    # Assert
    assert table_name == "agent_run"


def test_agent_run_dto_round_trips_entity_identity() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
    )

    # Act
    entity = AgentRunDTO.from_entity(agent_run).to_entity()

    # Assert
    assert entity == agent_run


def test_agent_run_dto_round_trips_run_fields() -> None:
    # Arrange
    agent_run = AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
        UserId.generate(),
    )
    agent_run.start()
    agent_run.complete("done")

    # Act
    entity = AgentRunDTO.from_entity(agent_run).to_entity()

    # Assert
    assert entity.workflow_name == agent_run.workflow_name
    assert entity.input_prompt == agent_run.input_prompt
    assert entity.status == AgentRunStatus.SUCCEEDED
    assert entity.created_by_user_id == agent_run.created_by_user_id
    assert entity.result == "done"
