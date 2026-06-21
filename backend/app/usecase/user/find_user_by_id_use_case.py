"""Provide the use case for retrieving one user."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import UserAccessDeniedError, UserNotFoundError
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import UserId


class FindUserByIdUseCase(ABC):
    """Define the application boundary for retrieving one user."""

    @abstractmethod
    async def execute(self, user_id: UserId, current_user: User) -> User:
        """Return a user visible to the current user."""


class FindUserByIdUseCaseImpl(FindUserByIdUseCase):
    """Find users while preserving access rules."""

    def __init__(self, user_repository: UserRepository):
        """Store use case dependencies."""
        self.user_repository = user_repository

    async def execute(self, user_id: UserId, current_user: User) -> User:
        """Return the requested user when access is allowed."""
        if user_id != current_user.id and not current_user.is_superuser:
            raise UserAccessDeniedError

        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        return user


def new_find_user_by_id_use_case(
    user_repository: UserRepository,
) -> FindUserByIdUseCase:
    """Instantiate the find-user-by-id use case."""
    return FindUserByIdUseCaseImpl(user_repository)
