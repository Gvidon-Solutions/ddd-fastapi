"""Define the User identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class UserId:
    """Represent the unique identifier for a user."""

    value: UUID

    @classmethod
    def generate(cls) -> "UserId":
        """Generate a new identifier for a user entity."""
        return cls(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
