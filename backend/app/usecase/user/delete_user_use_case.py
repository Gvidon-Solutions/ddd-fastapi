"""Provide the use case for administrator user deletion."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import (
    SuperuserSelfDeletionError,
    UserAccessDeniedError,
    UserNotFoundError,
)
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import UserId


class DeleteUserUseCase(ABC):
    """Define the application boundary for administrator user deletion."""

    @abstractmethod
    def execute(self, current_user: User, user_id: UserId) -> None:
        """Delete a user as an administrator."""


class DeleteUserUseCaseImpl(DeleteUserUseCase):
    """Delete users through repository abstractions."""

    def __init__(self, user_repository: UserRepository):
        """Store use case dependencies."""
        self.user_repository = user_repository

    def execute(self, current_user: User, user_id: UserId) -> None:
        """Delete a user when access rules allow it."""
        if not current_user.is_superuser:
            raise UserAccessDeniedError
        if current_user.id == user_id:
            raise SuperuserSelfDeletionError

        user = self.user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        self.user_repository.delete(user_id)


def new_delete_user_use_case(user_repository: UserRepository) -> DeleteUserUseCase:
    """Instantiate the administrator user delete use case."""
    return DeleteUserUseCaseImpl(user_repository)
