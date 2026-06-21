"""Use case test fakes."""

from app.domain.item.entities import Item
from app.domain.item.repositories import ItemRepository
from app.domain.item.value_objects import ItemId
from app.domain.user.entities import User
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, PasswordHash, UserId
from app.usecase.user.ports import PasswordHasher, PasswordVerificationResult


class InMemoryItemRepository(ItemRepository):
    """In-memory item repository for use case tests."""

    def __init__(self, items: list[Item] | None = None):
        self.items = {item.id: item for item in items or []}

    def save(self, item: Item) -> None:
        self.items[item.id] = item

    def find_by_id(self, item_id: ItemId) -> Item | None:
        return self.items.get(item_id)

    def find_all(self, offset: int = 0, limit: int = 100) -> list[Item]:
        return list(self.items.values())[offset : offset + limit]

    def find_by_owner_id(
        self,
        owner_id: UserId,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        items = [item for item in self.items.values() if item.owner_id == owner_id]
        return items[offset : offset + limit]

    def count(self) -> int:
        return len(self.items)

    def count_by_owner_id(self, owner_id: UserId) -> int:
        return len([item for item in self.items.values() if item.owner_id == owner_id])

    def delete(self, item_id: ItemId) -> None:
        self.items.pop(item_id, None)


class InMemoryUserRepository(UserRepository):
    """In-memory user repository for use case tests."""

    def __init__(self, users: list[User] | None = None):
        self.users = {user.id: user for user in users or []}

    def save(self, user: User) -> None:
        self.users[user.id] = user

    def find_by_id(self, user_id: UserId) -> User | None:
        return self.users.get(user_id)

    def find_by_email(self, email: EmailAddress) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    def find_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        return list(self.users.values())[offset : offset + limit]

    def count(self) -> int:
        return len(self.users)

    def delete(self, user_id: UserId) -> None:
        self.users.pop(user_id, None)


class FakePasswordHasher(PasswordHasher):
    """Predictable password hasher for use case tests."""

    def __init__(self, verified: bool = True, updated_hash: PasswordHash | None = None):
        self.verified = verified
        self.updated_hash = updated_hash

    def hash_password(self, plain_password: str) -> PasswordHash:
        return PasswordHash(f"hashed:{plain_password}")

    def verify_password(
        self,
        plain_password: str,
        hashed_password: PasswordHash,
    ) -> PasswordVerificationResult:
        return PasswordVerificationResult(
            verified=self.verified,
            updated_hash=self.updated_hash,
        )
