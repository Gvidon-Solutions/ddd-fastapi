"""Provide the use case for deleting items."""

from abc import ABC, abstractmethod

from app.domain.item.exceptions import ItemAccessDeniedError, ItemNotFoundError
from app.domain.item.repositories import ItemRepository
from app.domain.item.value_objects import ItemId
from app.domain.user.entities import User


class DeleteItemUseCase(ABC):
    """Define the application boundary for item deletion."""

    @abstractmethod
    def execute(self, current_user: User, item_id: ItemId) -> None:
        """Delete an item visible to the current user."""


class DeleteItemUseCaseImpl(DeleteItemUseCase):
    """Delete items while preserving owner/admin access rules."""

    def __init__(self, item_repository: ItemRepository):
        """Store use case dependencies."""
        self.item_repository = item_repository

    def execute(self, current_user: User, item_id: ItemId) -> None:
        """Delete an item when it exists and access is allowed."""
        item = self.item_repository.find_by_id(item_id)
        if item is None:
            raise ItemNotFoundError
        if not current_user.is_superuser and not item.is_owned_by(current_user.id):
            raise ItemAccessDeniedError

        self.item_repository.delete(item_id)


def new_delete_item_use_case(item_repository: ItemRepository) -> DeleteItemUseCase:
    """Instantiate the item delete use case."""
    return DeleteItemUseCaseImpl(item_repository)
