"""Provide the use case for retrieving one item."""

from abc import ABC, abstractmethod

from app.domain.item.entities import Item
from app.domain.item.exceptions import ItemAccessDeniedError, ItemNotFoundError
from app.domain.item.repositories import ItemRepository
from app.domain.item.value_objects import ItemId
from app.domain.user.entities import User


class FindItemByIdUseCase(ABC):
    """Define the application boundary for retrieving one item."""

    @abstractmethod
    def execute(self, current_user: User, item_id: ItemId) -> Item:
        """Return an item visible to the current user."""


class FindItemByIdUseCaseImpl(FindItemByIdUseCase):
    """Find items while preserving owner/admin access rules."""

    def __init__(self, item_repository: ItemRepository):
        """Store use case dependencies."""
        self.item_repository = item_repository

    def execute(self, current_user: User, item_id: ItemId) -> Item:
        """Return an item when it exists and access is allowed."""
        item = self.item_repository.find_by_id(item_id)
        if item is None:
            raise ItemNotFoundError
        if not current_user.is_superuser and not item.is_owned_by(current_user.id):
            raise ItemAccessDeniedError
        return item


def new_find_item_by_id_use_case(
    item_repository: ItemRepository,
) -> FindItemByIdUseCase:
    """Instantiate the find-item-by-id use case."""
    return FindItemByIdUseCaseImpl(item_repository)
