"""Define the Codex job identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CodexJobId:
    """Represent the unique identifier for a Codex job."""

    value: UUID

    @staticmethod
    def generate() -> "CodexJobId":
        """Generate a new identifier."""
        return CodexJobId(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
