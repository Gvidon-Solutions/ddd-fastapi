"""Provide the use case for authenticating users."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import InactiveUserError, InvalidCredentialsError
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress
from app.usecase.user.ports import PasswordHasher


class AuthenticateUserUseCase(ABC):
    """Define the application boundary for credential authentication."""

    @abstractmethod
    async def execute(self, email: EmailAddress, plain_password: str) -> User:
        """Authenticate a user and return the matching account."""


class AuthenticateUserUseCaseImpl(AuthenticateUserUseCase):
    """Authenticate users through repository and password hashing ports."""

    def __init__(
        self, user_repository: UserRepository, password_hasher: PasswordHasher
    ):
        """Store use case dependencies."""
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    async def execute(self, email: EmailAddress, plain_password: str) -> User:
        """Authenticate a user and refresh the hash when needed."""
        user = await self.user_repository.find_by_email(email)
        if user is None:
            raise InvalidCredentialsError

        result = self.password_hasher.verify_password(
            plain_password,
            user.hashed_password,
        )
        if not result.verified:
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        if result.updated_hash is not None:
            user.update_password_hash(result.updated_hash)
            await self.user_repository.save(user)

        return user


def new_authenticate_user_use_case(
    user_repository: UserRepository,
    password_hasher: PasswordHasher,
) -> AuthenticateUserUseCase:
    """Instantiate the user authentication use case."""
    return AuthenticateUserUseCaseImpl(user_repository, password_hasher)
