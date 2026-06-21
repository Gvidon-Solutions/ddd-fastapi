"""Define the AgentRun identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AgentRunId:
    """Represent the unique identifier for an agent run."""

    value: UUID

    @staticmethod
    def generate() -> "AgentRunId":
        """Generate a new identifier for an agent run."""
        return AgentRunId(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
