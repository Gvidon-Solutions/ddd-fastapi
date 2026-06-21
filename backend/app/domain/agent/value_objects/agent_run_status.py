"""Define agent run statuses."""

from enum import StrEnum


class AgentRunStatus(StrEnum):
    """Represent the lifecycle state of an agent run."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
