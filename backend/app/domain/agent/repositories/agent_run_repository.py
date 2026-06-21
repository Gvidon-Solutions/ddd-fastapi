"""Define the repository abstraction for agent runs."""

from abc import ABC, abstractmethod

from app.domain.agent.entities import AgentRun, AgentRunEvent
from app.domain.agent.value_objects import AgentRunId


class AgentRunRepository(ABC):
    """Provide the abstraction for agent run persistence operations."""

    @abstractmethod
    async def save(self, agent_run: AgentRun) -> None:
        """Persist the provided agent run."""

    @abstractmethod
    async def find_by_id(self, agent_run_id: AgentRunId) -> AgentRun | None:
        """Retrieve an agent run by its identifier."""

    @abstractmethod
    async def add_event(self, event: AgentRunEvent) -> None:
        """Persist an agent run event."""

    @abstractmethod
    async def find_events_by_run_id(
        self, agent_run_id: AgentRunId
    ) -> list[AgentRunEvent]:
        """Retrieve events emitted by an agent run."""
