"""Provide the use case for changing the current user's password."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import IncorrectPasswordError, PasswordReuseError
from app.domain.user.repositories import UserRepository
from app.usecase.user.ports import PasswordHasher


class UpdateCurrentUserPasswordUseCase(ABC):
    """Define the application boundary for current-user password changes."""

    @abstractmethod
    def execute(
        self,
        current_user: User,
        current_plain_password: str,
        new_plain_password: str,
    ) -> User:
        """Change the current user's password."""


class UpdateCurrentUserPasswordUseCaseImpl(UpdateCurrentUserPasswordUseCase):
    """Change a password through password hashing and user repository ports."""

    def __init__(
        self, user_repository: UserRepository, password_hasher: PasswordHasher
    ):
        """Store use case dependencies."""
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    def execute(
        self,
        current_user: User,
        current_plain_password: str,
        new_plain_password: str,
    ) -> User:
        """Verify the current password and persist a new password hash."""
        result = self.password_hasher.verify_password(
            current_plain_password,
            current_user.hashed_password,
        )
        if not result.verified:
            raise IncorrectPasswordError
        if current_plain_password == new_plain_password:
            raise PasswordReuseError

        current_user.update_password_hash(
            self.password_hasher.hash_password(new_plain_password)
        )
        self.user_repository.save(current_user)
        return current_user


def new_update_current_user_password_use_case(
    user_repository: UserRepository,
    password_hasher: PasswordHasher,
) -> UpdateCurrentUserPasswordUseCase:
    """Instantiate the current-user password update use case."""
    return UpdateCurrentUserPasswordUseCaseImpl(user_repository, password_hasher)
