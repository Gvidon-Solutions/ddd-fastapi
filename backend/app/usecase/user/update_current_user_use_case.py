"""Provide the use case for updating the current user's profile."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import EmailAlreadyExistsError
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, FullName


class UpdateCurrentUserUseCase(ABC):
    """Define the application boundary for current-user profile updates."""

    @abstractmethod
    def execute(
        self,
        current_user: User,
        email: EmailAddress | None = None,
        full_name: FullName | None = None,
    ) -> User:
        """Update the current user's profile."""


class UpdateCurrentUserUseCaseImpl(UpdateCurrentUserUseCase):
    """Update current-user profile fields with uniqueness checks."""

    def __init__(self, user_repository: UserRepository):
        """Store use case dependencies."""
        self.user_repository = user_repository

    def execute(
        self,
        current_user: User,
        email: EmailAddress | None = None,
        full_name: FullName | None = None,
    ) -> User:
        """Persist updates for the current user's profile."""
        if email is not None and email != current_user.email:
            existing_user = self.user_repository.find_by_email(email)
            if existing_user is not None and existing_user.id != current_user.id:
                raise EmailAlreadyExistsError
            current_user.update_email(email)

        if full_name is not None:
            current_user.update_full_name(full_name)

        self.user_repository.save(current_user)
        return current_user


def new_update_current_user_use_case(
    user_repository: UserRepository,
) -> UpdateCurrentUserUseCase:
    """Instantiate the current-user update use case."""
    return UpdateCurrentUserUseCaseImpl(user_repository)
