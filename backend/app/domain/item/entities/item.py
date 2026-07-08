"""Define the Item aggregate root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.item.value_objects import (
    ItemDescription,
    ItemId,
    ItemTitle,
    new_item_id,
)
from app.domain.user.value_objects import UserId


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(eq=False)
class Item:
    """Represent an item owned by a user."""

    id: ItemId
    owner_id: UserId
    title: ItemTitle
    description: ItemDescription | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __hash__(self) -> int:
        """Return a hash value based on the entity identity."""
        return hash(self.id)

    def __eq__(self, obj: object) -> bool:
        """Compare items by identifier."""
        if isinstance(obj, Item):
            return self.id == obj.id
        return False

    def update_content(
        self,
        title: ItemTitle,
        description: ItemDescription | None = None,
    ) -> None:
        """Replace the item content."""
        self.title = title
        self.description = description

    def is_owned_by(self, user_id: UserId) -> bool:
        """Return whether the item belongs to the provided user."""
        return self.owner_id == user_id

    @classmethod
    def create(
        cls,
        owner_id: UserId,
        title: ItemTitle,
        description: ItemDescription | None = None,
    ) -> "Item":
        """Create a new item with a generated identifier."""
        return cls(
            id=new_item_id(),
            owner_id=owner_id,
            title=title,
            description=description,
        )
