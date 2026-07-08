"""Item response schema."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.domain.item.entities import Item


class ItemPublic(SQLModel):
    """Item response schema."""

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    created_at: datetime | None = None

    @classmethod
    def from_entity(cls, item: Item) -> "ItemPublic":
        """Build an API response from a domain entity."""
        return cls(
            id=item.id,
            owner_id=item.owner_id,
            title=item.title.value,
            description=item.description.value if item.description else None,
            created_at=item.created_at,
        )
