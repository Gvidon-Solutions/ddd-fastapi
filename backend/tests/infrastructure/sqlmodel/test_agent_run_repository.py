"""Agent run SQLModel repository tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.agent.entities import AgentRun, AgentRunEvent
from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentPrompt,
    AgentRunStatus,
    AgentWorkflowName,
)
from app.infrastructure.sqlmodel.agent import new_agent_run_repository

pytestmark = pytest.mark.anyio


def _agent_run() -> AgentRun:
    return AgentRun.create(
        AgentWorkflowName("agentic_requirements_review"),
        AgentPrompt("Review requirements"),
    )


async def test_agent_run_repository_persists_run(db_session: AsyncSession) -> None:
    # Arrange
    repository = new_agent_run_repository(db_session)
    agent_run = _agent_run()

    # Act
    await repository.save(agent_run)
    await db_session.commit()

    # Assert
    assert await repository.find_by_id(agent_run.id) == agent_run


async def test_agent_run_repository_updates_run(db_session: AsyncSession) -> None:
    # Arrange
    repository = new_agent_run_repository(db_session)
    agent_run = _agent_run()
    await repository.save(agent_run)
    await db_session.commit()
    agent_run.start()
    agent_run.complete("done")

    # Act
    await repository.save(agent_run)
    await db_session.commit()

    # Assert
    found = await repository.find_by_id(agent_run.id)
    assert found is not None
    assert found.status == AgentRunStatus.SUCCEEDED
    assert found.result == "done"


async def test_agent_run_repository_persists_events(
    db_session: AsyncSession,
) -> None:
    # Arrange
    repository = new_agent_run_repository(db_session)
    agent_run = _agent_run()
    await repository.save(agent_run)
    await db_session.commit()
    event = AgentRunEvent.create(
        agent_run.id,
        AgentEventType.STARTED,
        AgentEventPayload({"message": "started"}),
    )

    # Act
    await repository.add_event(event)
    await db_session.commit()

    # Assert
    events = await repository.find_events_by_run_id(agent_run.id)
    assert len(events) == 1
    assert events[0].run_id == event.run_id
    assert events[0].event_type == event.event_type
    assert events[0].payload == event.payload
