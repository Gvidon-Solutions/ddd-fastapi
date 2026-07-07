"""Define the Job identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class JobId:
    """Represent the unique identifier for a job."""

    value: UUID

    @classmethod
    def generate(cls) -> "JobId":
        """Generate a new identifier for a job."""
        return cls(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
