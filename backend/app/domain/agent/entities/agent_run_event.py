"""Define the AgentRunEvent entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentRunId,
)


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class AgentRunEvent:
    """Represent a point-in-time event emitted by an agent run."""

    run_id: AgentRunId
    event_type: AgentEventType
    payload: AgentEventPayload
    created_at: datetime = field(default_factory=_utc_now)

    @staticmethod
    def create(
        run_id: AgentRunId,
        event_type: AgentEventType,
        payload: AgentEventPayload,
    ) -> "AgentRunEvent":
        """Create a new agent run event."""
        return AgentRunEvent(
            run_id=run_id,
            event_type=event_type,
            payload=payload,
        )
