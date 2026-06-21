"""Define the Item identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ItemId:
    """Represent the unique identifier for an item."""

    value: UUID

    @staticmethod
    def generate() -> "ItemId":
        """Generate a new identifier for an item entity."""
        return ItemId(uuid4())

    def __str__(self) -> str:
        """Return the string representation of the UUID."""
        return str(self.value)
