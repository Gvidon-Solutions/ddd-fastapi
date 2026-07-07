"""Define the File identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class FileId:
    """Represent the unique identifier for a file."""

    value: UUID

    @classmethod
    def generate(cls) -> "FileId":
        """Generate a new identifier for a file."""
        return cls(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
