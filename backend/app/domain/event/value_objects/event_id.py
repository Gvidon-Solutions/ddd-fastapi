"""Define the Event identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EventId:
    """Represent the unique identifier for an event."""

    value: UUID

    @classmethod
    def generate(cls) -> "EventId":
        """Generate a new identifier for an event."""
        return cls(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
