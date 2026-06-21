"""Provide the use case for updating items."""

from abc import ABC, abstractmethod

from app.domain.item.entities import Item
from app.domain.item.exceptions import ItemAccessDeniedError, ItemNotFoundError
from app.domain.item.repositories import ItemRepository
from app.domain.item.value_objects import ItemDescription, ItemId, ItemTitle
from app.domain.user.entities import User


class UpdateItemUseCase(ABC):
    """Define the application boundary for item updates."""

    @abstractmethod
    async def execute(
        self,
        current_user: User,
        item_id: ItemId,
        title: ItemTitle | None = None,
        description: ItemDescription | None = None,
    ) -> Item:
        """Update an item visible to the current user."""


class UpdateItemUseCaseImpl(UpdateItemUseCase):
    """Update items while preserving owner/admin access rules."""

    def __init__(self, item_repository: ItemRepository):
        """Store use case dependencies."""
        self.item_repository = item_repository

    async def execute(
        self,
        current_user: User,
        item_id: ItemId,
        title: ItemTitle | None = None,
        description: ItemDescription | None = None,
    ) -> Item:
        """Update and persist an item."""
        item = await self.item_repository.find_by_id(item_id)
        if item is None:
            raise ItemNotFoundError
        if not current_user.is_superuser and not item.is_owned_by(current_user.id):
            raise ItemAccessDeniedError

        item.update_content(title=title or item.title, description=description)
        await self.item_repository.save(item)
        return item


def new_update_item_use_case(item_repository: ItemRepository) -> UpdateItemUseCase:
    """Instantiate the item update use case."""
    return UpdateItemUseCaseImpl(item_repository)
