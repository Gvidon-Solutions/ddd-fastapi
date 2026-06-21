"""Define the repository abstraction for item entities."""

from abc import ABC, abstractmethod

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemId
from app.domain.user.value_objects import UserId


class ItemRepository(ABC):
    """Provide the abstraction for item persistence operations."""

    @abstractmethod
    async def save(self, item: Item) -> None:
        """Persist the provided item entity."""

    @abstractmethod
    async def find_by_id(self, item_id: ItemId) -> Item | None:
        """Retrieve an item by its identifier."""

    @abstractmethod
    async def find_all(self, offset: int = 0, limit: int = 100) -> list[Item]:
        """Return items ordered by repository policy."""

    @abstractmethod
    async def find_by_owner_id(
        self,
        owner_id: UserId,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        """Return items owned by the provided user."""

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of items."""

    @abstractmethod
    async def count_by_owner_id(self, owner_id: UserId) -> int:
        """Return the total number of items owned by the provided user."""

    @abstractmethod
    async def delete(self, item_id: ItemId) -> None:
        """Remove an item by its identifier."""
