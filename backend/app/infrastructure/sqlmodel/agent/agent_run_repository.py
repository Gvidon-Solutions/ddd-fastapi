"""SQLModel implementation of the agent run repository."""

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.agent.entities import AgentRun, AgentRunEvent
from app.domain.agent.repositories import AgentRunRepository
from app.domain.agent.value_objects import AgentRunId
from app.infrastructure.sqlmodel.agent.agent_run_dto import AgentRunDTO
from app.infrastructure.sqlmodel.agent.agent_run_event_dto import AgentRunEventDTO


class AgentRunRepositoryImpl(AgentRunRepository):
    """Persist agent runs and events with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def save(self, agent_run: AgentRun) -> None:
        """Insert or update an agent run."""
        agent_run_dto = AgentRunDTO.from_entity(agent_run)
        existing_run = await self.session.get(AgentRunDTO, agent_run.id.value)
        if existing_run is None:
            self.session.add(agent_run_dto)
            return

        existing_run.workflow_name = agent_run_dto.workflow_name
        existing_run.input_prompt = agent_run_dto.input_prompt
        existing_run.status = agent_run_dto.status
        existing_run.created_by_user_id = agent_run_dto.created_by_user_id
        existing_run.result = agent_run_dto.result
        existing_run.error_message = agent_run_dto.error_message
        existing_run.created_at = agent_run_dto.created_at
        existing_run.started_at = agent_run_dto.started_at
        existing_run.finished_at = agent_run_dto.finished_at
        self.session.add(existing_run)

    async def find_by_id(self, agent_run_id: AgentRunId) -> AgentRun | None:
        """Return an agent run by ID."""
        agent_run = await self.session.get(AgentRunDTO, agent_run_id.value)
        return agent_run.to_entity() if agent_run else None

    async def add_event(self, event: AgentRunEvent) -> None:
        """Insert an agent run event."""
        self.session.add(AgentRunEventDTO.from_entity(event))

    async def find_events_by_run_id(
        self,
        agent_run_id: AgentRunId,
    ) -> list[AgentRunEvent]:
        """Return events emitted by an agent run ordered oldest first."""
        statement = (
            select(AgentRunEventDTO)
            .where(AgentRunEventDTO.run_id == agent_run_id.value)
            .order_by(col(AgentRunEventDTO.created_at).asc())
        )
        result = await self.session.exec(statement)
        return [event.to_entity() for event in result.all()]


def new_agent_run_repository(session: AsyncSession) -> AgentRunRepository:
    """Create an agent run repository bound to the active session."""
    return AgentRunRepositoryImpl(session)
