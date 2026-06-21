"""Agent Taskiq runner tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.agent.entities import AgentRun, AgentRunEvent
from app.domain.agent.value_objects import (
    AgentPrompt,
    AgentRunStatus,
    AgentWorkflowName,
)
from app.infrastructure.sqlmodel.agent import new_agent_run_repository
from app.infrastructure.taskiq.agent_runner import run_agent_workflow_in_session

pytestmark = pytest.mark.anyio


async def test_run_agent_workflow_in_session_completes_run(
    db_session: AsyncSession,
) -> None:
    # Arrange
    published_events: list[AgentRunEvent] = []
    repository = new_agent_run_repository(db_session)
    agent_run = AgentRun.create(
        workflow_name=AgentWorkflowName("codex_review"),
        input_prompt=AgentPrompt("Review this repository"),
    )
    await repository.save(agent_run)
    await db_session.commit()

    async def publish_event(event: AgentRunEvent) -> None:
        published_events.append(event)

    # Act
    result = await run_agent_workflow_in_session(
        agent_run.id,
        db_session,
        publish_event,
    )

    # Assert
    found = await repository.find_by_id(agent_run.id)
    events = await repository.find_events_by_run_id(agent_run.id)
    assert found is not None
    assert found.status == AgentRunStatus.SUCCEEDED
    assert found.result == result
    assert [event.event_type for event in events] == [
        event.event_type for event in published_events
    ]
