"""Execute queued agent runs from Taskiq workers."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.agent.entities import AgentRunEvent
from app.domain.agent.repositories import AgentRunRepository
from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentRunId,
)
from app.infrastructure.di.injection import engine
from app.infrastructure.openai_agents import new_agent_workflow_runner
from app.infrastructure.sqlmodel.agent import new_agent_run_repository
from app.infrastructure.stream import publish_agent_run_event
from app.usecase.agent import AgentWorkflowRunner

Commit = Callable[[], Awaitable[None]]
PublishAgentRunEvent = Callable[[AgentRunEvent], Awaitable[None]]


def _event(
    agent_run_id: AgentRunId,
    event_type: AgentEventType,
    message: str,
) -> AgentRunEvent:
    """Create a simple status event for an agent run."""
    return AgentRunEvent.create(
        run_id=agent_run_id,
        event_type=event_type,
        payload=AgentEventPayload({"message": message}),
    )


async def _save_event(
    repository: AgentRunRepository,
    event: AgentRunEvent,
    commit: Commit,
    publish_event: PublishAgentRunEvent,
) -> None:
    """Persist, commit, and publish one agent run event."""
    await repository.add_event(event)
    await commit()
    await publish_event(event)


async def execute_agent_workflow(
    agent_run_id: AgentRunId,
    repository: AgentRunRepository,
    commit: Commit,
    rollback: Commit,
    publish_event: PublishAgentRunEvent,
    workflow_runner: AgentWorkflowRunner | None = None,
) -> str:
    """Execute one agent workflow and persist its state transitions."""
    agent_run = await repository.find_by_id(agent_run_id)
    if agent_run is None:
        raise ValueError(f"Agent run {agent_run_id} was not found")

    try:
        agent_run.start()
        await repository.save(agent_run)
        await _save_event(
            repository,
            _event(agent_run.id, AgentEventType.STARTED, "Agent run started"),
            commit,
            publish_event,
        )

        runner = workflow_runner or new_agent_workflow_runner(agent_run.workflow_name)

        async def emit_event(event: AgentRunEvent) -> None:
            await _save_event(repository, event, commit, publish_event)

        result = await runner.execute(agent_run, emit_event)
        agent_run.complete(result)
        await repository.save(agent_run)
        await _save_event(
            repository,
            _event(agent_run.id, AgentEventType.COMPLETED, "Agent run completed"),
            commit,
            publish_event,
        )
    except Exception as error:
        await rollback()
        agent_run.fail(str(error))
        await repository.save(agent_run)
        await _save_event(
            repository,
            _event(agent_run.id, AgentEventType.FAILED, str(error)),
            commit,
            publish_event,
        )
        raise

    return result


async def run_agent_workflow_in_session(
    agent_run_id: AgentRunId,
    session: AsyncSession,
    publish_event: PublishAgentRunEvent = publish_agent_run_event,
    workflow_runner: AgentWorkflowRunner | None = None,
) -> str:
    """Execute an agent workflow using the provided database session."""
    return await execute_agent_workflow(
        agent_run_id=agent_run_id,
        repository=new_agent_run_repository(session),
        commit=session.commit,
        rollback=session.rollback,
        publish_event=publish_event,
        workflow_runner=workflow_runner,
    )


async def run_agent_workflow(agent_run_id: str) -> str:
    """Taskiq entrypoint for executing an agent workflow by ID."""
    parsed_agent_run_id = AgentRunId(UUID(agent_run_id))
    async with AsyncSession(engine) as session:
        return await run_agent_workflow_in_session(parsed_agent_run_id, session)
