"""Item SQLModel DTO."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemId, ItemTitle
from app.domain.user.value_objects import UserId
from app.infrastructure.sqlmodel.datetime import get_datetime_utc

if TYPE_CHECKING:
    from app.infrastructure.sqlmodel.user.user_dto import UserDTO


class ItemDTO(SQLModel, table=True):
    """Persisted item record."""

    __tablename__ = "item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
    )
    owner: Optional["UserDTO"] = Relationship(back_populates="items")

    def to_entity(self) -> Item:
        """Convert this persistence DTO to a domain entity."""
        return Item(
            id=ItemId(self.id),
            owner_id=UserId(self.owner_id),
            title=ItemTitle(self.title),
            description=ItemDescription(self.description)
            if self.description is not None
            else None,
            created_at=self.created_at or get_datetime_utc(),
        )

    @classmethod
    def from_entity(cls, item: Item) -> "ItemDTO":
        """Build a persistence DTO from a domain entity."""
        return cls(
            id=item.id,
            owner_id=item.owner_id,
            title=item.title.value,
            description=item.description.value if item.description else None,
            created_at=item.created_at,
        )
