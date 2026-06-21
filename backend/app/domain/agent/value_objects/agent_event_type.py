"""Define agent run event types."""

from enum import StrEnum


class AgentEventType(StrEnum):
    """Represent the type of an agent run event."""

    QUEUED = "queued"
    STARTED = "started"
    STEP = "step"
    TOOL_CALL = "tool_call"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
