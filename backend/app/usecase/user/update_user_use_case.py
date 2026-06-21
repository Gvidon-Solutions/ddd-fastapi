"""Provide the use case for administrator user updates."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import (
    EmailAlreadyExistsError,
    UserAccessDeniedError,
    UserNotFoundError,
)
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, FullName, UserId
from app.usecase.user.ports import PasswordHasher


class UpdateUserUseCase(ABC):
    """Define the application boundary for administrator user updates."""

    @abstractmethod
    async def execute(
        self,
        current_user: User,
        user_id: UserId,
        email: EmailAddress | None = None,
        full_name: FullName | None = None,
        plain_password: str | None = None,
        *,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> User:
        """Update a user as an administrator."""


class UpdateUserUseCaseImpl(UpdateUserUseCase):
    """Update users through domain and repository abstractions."""

    def __init__(
        self, user_repository: UserRepository, password_hasher: PasswordHasher
    ):
        """Store use case dependencies."""
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    async def execute(
        self,
        current_user: User,
        user_id: UserId,
        email: EmailAddress | None = None,
        full_name: FullName | None = None,
        plain_password: str | None = None,
        *,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> User:
        """Update and persist a user."""
        if not current_user.is_superuser:
            raise UserAccessDeniedError

        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        if email is not None and email != user.email:
            existing_user = await self.user_repository.find_by_email(email)
            if existing_user is not None and existing_user.id != user.id:
                raise EmailAlreadyExistsError
            user.update_email(email)

        if full_name is not None:
            user.update_full_name(full_name)
        if plain_password is not None:
            user.update_password_hash(
                self.password_hasher.hash_password(plain_password)
            )
        if is_active is not None:
            if is_active:
                user.activate()
            else:
                user.deactivate()
        if is_superuser is not None:
            if is_superuser:
                user.grant_superuser()
            else:
                user.revoke_superuser()

        await self.user_repository.save(user)
        return user


def new_update_user_use_case(
    user_repository: UserRepository,
    password_hasher: PasswordHasher,
) -> UpdateUserUseCase:
    """Instantiate the administrator user update use case."""
    return UpdateUserUseCaseImpl(user_repository, password_hasher)
