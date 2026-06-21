"""Agent workflow execution port."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.domain.agent.entities import AgentRun, AgentRunEvent

EmitAgentRunEvent = Callable[[AgentRunEvent], Awaitable[None]]


class AgentWorkflowRunner(ABC):
    """Execute a persisted agent workflow run."""

    @abstractmethod
    async def execute(
        self,
        agent_run: AgentRun,
        emit_event: EmitAgentRunEvent,
    ) -> str:
        """Run the workflow and return final output."""
