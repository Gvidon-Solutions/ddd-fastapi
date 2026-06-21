"""Shared test fixtures."""

from collections.abc import Generator

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash
from app.infrastructure.sqlmodel.item import ItemDTO
from app.infrastructure.sqlmodel.user import UserDTO


@pytest.fixture
def user() -> User:
    """Return a regular test user."""
    return User.create(
        email=EmailAddress("user@example.com"),
        hashed_password=PasswordHash("hash"),
        full_name=FullName("Regular User"),
    )


@pytest.fixture
def admin() -> User:
    """Return an admin test user."""
    return User.create(
        email=EmailAddress("admin@example.com"),
        hashed_password=PasswordHash("hash"),
        full_name=FullName("Admin User"),
        is_superuser=True,
    )


@pytest.fixture
def item(user: User) -> Item:
    """Return an item owned by the regular test user."""
    return Item.create(
        owner_id=user.id,
        title=ItemTitle("Item"),
        description=ItemDescription("Description"),
    )


@pytest.fixture
def db_session() -> Generator[Session]:
    """Yield an in-memory SQLModel session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Import DTOs before create_all so relationship metadata is registered.
    assert UserDTO.__tablename__ == "user"
    assert ItemDTO.__tablename__ == "item"
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
