"""Provide the public user registration use case."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import EmailAlreadyExistsError
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, FullName
from app.usecase.user.ports import PasswordHasher


class RegisterUserUseCase(ABC):
    """Define the application boundary for public registration."""

    @abstractmethod
    async def execute(
        self,
        email: EmailAddress,
        plain_password: str,
        full_name: FullName | None = None,
    ) -> User:
        """Register a new regular user."""


class RegisterUserUseCaseImpl(RegisterUserUseCase):
    """Register regular users through domain and repository abstractions."""

    def __init__(
        self, user_repository: UserRepository, password_hasher: PasswordHasher
    ):
        """Store use case dependencies."""
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    async def execute(
        self,
        email: EmailAddress,
        plain_password: str,
        full_name: FullName | None = None,
    ) -> User:
        """Create, persist, and return a new regular user."""
        if await self.user_repository.find_by_email(email) is not None:
            raise EmailAlreadyExistsError

        user = User.create(
            email=email,
            hashed_password=self.password_hasher.hash_password(plain_password),
            full_name=full_name,
            is_superuser=False,
        )
        await self.user_repository.save(user)
        return user


def new_register_user_use_case(
    user_repository: UserRepository,
    password_hasher: PasswordHasher,
) -> RegisterUserUseCase:
    """Instantiate the public registration use case."""
    return RegisterUserUseCaseImpl(user_repository, password_hasher)
