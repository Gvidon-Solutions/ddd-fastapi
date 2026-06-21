"""Define the AgentRun aggregate root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.agent.value_objects import (
    AgentPrompt,
    AgentRunId,
    AgentRunStatus,
    AgentWorkflowName,
)
from app.domain.user.value_objects import UserId


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(eq=False)
class AgentRun:
    """Represent one requested agent workflow execution."""

    id: AgentRunId
    workflow_name: AgentWorkflowName
    input_prompt: AgentPrompt
    status: AgentRunStatus = AgentRunStatus.QUEUED
    created_by_user_id: UserId | None = None
    result: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def __hash__(self) -> int:
        """Return a hash value based on the entity identity."""
        return hash(self.id)

    def __eq__(self, obj: object) -> bool:
        """Compare agent runs by identifier."""
        if isinstance(obj, AgentRun):
            return self.id == obj.id
        return False

    def start(self) -> None:
        """Mark the run as started."""
        self.status = AgentRunStatus.RUNNING
        self.started_at = _utc_now()

    def complete(self, result: str) -> None:
        """Mark the run as completed."""
        self.status = AgentRunStatus.SUCCEEDED
        self.result = result
        self.error_message = None
        self.finished_at = _utc_now()

    def fail(self, error_message: str) -> None:
        """Mark the run as failed."""
        self.status = AgentRunStatus.FAILED
        self.error_message = error_message
        self.finished_at = _utc_now()

    def cancel(self) -> None:
        """Mark the run as cancelled."""
        self.status = AgentRunStatus.CANCELLED
        self.finished_at = _utc_now()

    @staticmethod
    def create(
        workflow_name: AgentWorkflowName,
        input_prompt: AgentPrompt,
        created_by_user_id: UserId | None = None,
    ) -> "AgentRun":
        """Create a new queued agent run."""
        return AgentRun(
            id=AgentRunId.generate(),
            workflow_name=workflow_name,
            input_prompt=input_prompt,
            created_by_user_id=created_by_user_id,
        )
