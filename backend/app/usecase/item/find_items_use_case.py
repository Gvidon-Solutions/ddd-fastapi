"""Provide the use case for listing items."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.item.entities import Item
from app.domain.item.repositories import ItemRepository
from app.domain.user.entities import User


@dataclass(frozen=True)
class FindItemsResult:
    """Represent a paginated item listing result."""

    data: list[Item]
    count: int


class FindItemsUseCase(ABC):
    """Define the application boundary for listing items."""

    @abstractmethod
    async def execute(
        self,
        current_user: User,
        offset: int = 0,
        limit: int = 100,
    ) -> FindItemsResult:
        """Return items visible to the current user."""


class FindItemsUseCaseImpl(FindItemsUseCase):
    """List all items for admins and owned items for regular users."""

    def __init__(self, item_repository: ItemRepository):
        """Store use case dependencies."""
        self.item_repository = item_repository

    async def execute(
        self,
        current_user: User,
        offset: int = 0,
        limit: int = 100,
    ) -> FindItemsResult:
        """Return a paginated item list."""
        if current_user.is_superuser:
            return FindItemsResult(
                data=await self.item_repository.find_all(offset=offset, limit=limit),
                count=await self.item_repository.count(),
            )

        return FindItemsResult(
            data=await self.item_repository.find_by_owner_id(
                current_user.id,
                offset=offset,
                limit=limit,
            ),
            count=await self.item_repository.count_by_owner_id(current_user.id),
        )


def new_find_items_use_case(item_repository: ItemRepository) -> FindItemsUseCase:
    """Instantiate the find-items use case."""
    return FindItemsUseCaseImpl(item_repository)
