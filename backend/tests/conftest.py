"""Shared test fixtures."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash
from app.infrastructure.sqlmodel.item import ItemDTO
from app.infrastructure.sqlmodel.job import JobArtifactDTO, JobDTO, JobEventDTO
from app.infrastructure.sqlmodel.user import UserDTO


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio."""
    return "asyncio"


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
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Yield an in-memory SQLModel session."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Import DTOs before create_all so relationship metadata is registered.
    assert UserDTO.__tablename__ == "user"
    assert ItemDTO.__tablename__ == "item"
    assert JobDTO.__tablename__ == "job"
    assert JobArtifactDTO.__tablename__ == "job_artifact"
    assert JobEventDTO.__tablename__ == "job_event"
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    await engine.dispose()
