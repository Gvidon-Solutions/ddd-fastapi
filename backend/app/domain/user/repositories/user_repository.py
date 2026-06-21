"""Define the repository abstraction for user entities."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, UserId


class UserRepository(ABC):
    """Provide the abstraction for user persistence operations."""

    @abstractmethod
    def save(self, user: User) -> None:
        """Persist the provided user entity."""

    @abstractmethod
    def find_by_id(self, user_id: UserId) -> User | None:
        """Retrieve a user by its identifier."""

    @abstractmethod
    def find_by_email(self, email: EmailAddress) -> User | None:
        """Retrieve a user by its email address."""

    @abstractmethod
    def find_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        """Return users ordered by repository policy."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of users."""

    @abstractmethod
    def delete(self, user_id: UserId) -> None:
        """Remove a user by its identifier."""
