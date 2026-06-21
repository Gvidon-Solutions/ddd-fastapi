"""Provide the use case for creating items."""

from abc import ABC, abstractmethod

from app.domain.item.entities import Item
from app.domain.item.repositories import ItemRepository
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.entities import User


class CreateItemUseCase(ABC):
    """Define the application boundary for item creation."""

    @abstractmethod
    async def execute(
        self,
        current_user: User,
        title: ItemTitle,
        description: ItemDescription | None = None,
    ) -> Item:
        """Create an item owned by the current user."""


class CreateItemUseCaseImpl(CreateItemUseCase):
    """Create items through repository abstractions."""

    def __init__(self, item_repository: ItemRepository):
        """Store use case dependencies."""
        self.item_repository = item_repository

    async def execute(
        self,
        current_user: User,
        title: ItemTitle,
        description: ItemDescription | None = None,
    ) -> Item:
        """Create, persist, and return a new item."""
        item = Item.create(
            owner_id=current_user.id,
            title=title,
            description=description,
        )
        await self.item_repository.save(item)
        return item


def new_create_item_use_case(item_repository: ItemRepository) -> CreateItemUseCase:
    """Instantiate the item creation use case."""
    return CreateItemUseCaseImpl(item_repository)
