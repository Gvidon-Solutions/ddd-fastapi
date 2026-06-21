"""User SQLModel repository tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash
from app.infrastructure.sqlmodel.user import new_user_repository

pytestmark = pytest.mark.anyio


async def test_user_repository_persists_user(db_session: AsyncSession) -> None:
    # Arrange
    repository = new_user_repository(db_session)
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))

    # Act
    await repository.save(user)
    await db_session.commit()

    # Assert
    assert await repository.find_by_email(EmailAddress("user@example.com")) == user


async def test_user_repository_counts_users(db_session: AsyncSession) -> None:
    # Arrange
    repository = new_user_repository(db_session)
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))
    await repository.save(user)
    await db_session.commit()

    # Act
    count = await repository.count()

    # Assert
    assert count == 1


async def test_user_repository_updates_user(db_session: AsyncSession) -> None:
    # Arrange
    repository = new_user_repository(db_session)
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))
    await repository.save(user)
    await db_session.commit()
    user.update_full_name(FullName("Updated"))

    # Act
    await repository.save(user)
    await db_session.commit()

    # Assert
    found = await repository.find_by_id(user.id)
    assert found is not None
    assert found.full_name == FullName("Updated")


async def test_user_repository_deletes_user(db_session: AsyncSession) -> None:
    # Arrange
    repository = new_user_repository(db_session)
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))
    await repository.save(user)
    await db_session.commit()

    # Act
    await repository.delete(user.id)
    await db_session.commit()

    # Assert
    assert await repository.find_by_id(user.id) is None
