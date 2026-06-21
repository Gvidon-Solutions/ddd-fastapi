"""Paginated items response schema."""

from sqlmodel import SQLModel

from app.presentation.api.item.schemas.item_public import ItemPublic


class ItemsPublic(SQLModel):
    """Paginated items response."""

    data: list[ItemPublic]
    count: int
