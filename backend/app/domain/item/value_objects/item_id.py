"""Define the Item identifier type."""

from typing import NewType
from uuid import UUID, uuid4

ItemId = NewType("ItemId", UUID)


def new_item_id() -> ItemId:
    """Generate a new identifier for an item entity."""
    return ItemId(uuid4())
