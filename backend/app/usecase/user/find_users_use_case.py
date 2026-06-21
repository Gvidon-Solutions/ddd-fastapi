"""Provide the use case for listing users."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.user.entities import User
from app.domain.user.exceptions import UserAccessDeniedError
from app.domain.user.repositories import UserRepository


@dataclass(frozen=True)
class FindUsersResult:
    """Represent a paginated user listing result."""

    data: list[User]
    count: int


class FindUsersUseCase(ABC):
    """Define the application boundary for listing users."""

    @abstractmethod
    async def execute(
        self,
        current_user: User,
        offset: int = 0,
        limit: int = 100,
    ) -> FindUsersResult:
        """Return users visible to the current user."""


class FindUsersUseCaseImpl(FindUsersUseCase):
    """List users for administrators."""

    def __init__(self, user_repository: UserRepository):
        """Store use case dependencies."""
        self.user_repository = user_repository

    async def execute(
        self,
        current_user: User,
        offset: int = 0,
        limit: int = 100,
    ) -> FindUsersResult:
        """Return a paginated user list."""
        if not current_user.is_superuser:
            raise UserAccessDeniedError

        return FindUsersResult(
            data=await self.user_repository.find_all(offset=offset, limit=limit),
            count=await self.user_repository.count(),
        )


def new_find_users_use_case(user_repository: UserRepository) -> FindUsersUseCase:
    """Instantiate the find-users use case."""
    return FindUsersUseCaseImpl(user_repository)
