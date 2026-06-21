"""Provide the use case for creating users as an administrator."""

from abc import ABC, abstractmethod

from app.domain.user.entities import User
from app.domain.user.exceptions import EmailAlreadyExistsError
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, FullName
from app.usecase.user.ports import PasswordHasher


class CreateUserUseCase(ABC):
    """Define the application boundary for administrator user creation."""

    @abstractmethod
    def execute(
        self,
        email: EmailAddress,
        plain_password: str,
        full_name: FullName | None = None,
        *,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> User:
        """Create a user."""


class CreateUserUseCaseImpl(CreateUserUseCase):
    """Create users through repository and password hashing ports."""

    def __init__(
        self, user_repository: UserRepository, password_hasher: PasswordHasher
    ):
        """Store use case dependencies."""
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    def execute(
        self,
        email: EmailAddress,
        plain_password: str,
        full_name: FullName | None = None,
        *,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> User:
        """Create, persist, and return a new user."""
        if self.user_repository.find_by_email(email) is not None:
            raise EmailAlreadyExistsError

        user = User.create(
            email=email,
            hashed_password=self.password_hasher.hash_password(plain_password),
            full_name=full_name,
            is_superuser=is_superuser,
        )
        if not is_active:
            user.deactivate()

        self.user_repository.save(user)
        return user


def new_create_user_use_case(
    user_repository: UserRepository,
    password_hasher: PasswordHasher,
) -> CreateUserUseCase:
    """Instantiate the administrator user creation use case."""
    return CreateUserUseCaseImpl(user_repository, password_hasher)
