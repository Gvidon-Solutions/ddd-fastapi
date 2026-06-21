"""Item SQLModel repository tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, PasswordHash
from app.infrastructure.sqlmodel.item import new_item_repository
from app.infrastructure.sqlmodel.user import new_user_repository

pytestmark = pytest.mark.anyio


async def _save_user(db_session: AsyncSession, email: str) -> User:
    user = User.create(EmailAddress(email), PasswordHash("hash"))
    await new_user_repository(db_session).save(user)
    return user


async def test_item_repository_persists_item(db_session: AsyncSession) -> None:
    # Arrange
    owner = await _save_user(db_session, "owner@example.com")
    repository = new_item_repository(db_session)
    item = Item.create(owner.id, ItemTitle("Owner item"), ItemDescription("Body"))

    # Act
    await repository.save(item)
    await db_session.commit()

    # Assert
    assert await repository.find_by_id(item.id) == item


async def test_item_repository_counts_items(db_session: AsyncSession) -> None:
    # Arrange
    owner = await _save_user(db_session, "owner@example.com")
    other = await _save_user(db_session, "other@example.com")
    repository = new_item_repository(db_session)
    await repository.save(Item.create(owner.id, ItemTitle("Owner item")))
    await repository.save(Item.create(other.id, ItemTitle("Other item")))
    await db_session.commit()

    # Act
    count = await repository.count()

    # Assert
    assert count == 2


async def test_item_repository_counts_items_by_owner(db_session: AsyncSession) -> None:
    # Arrange
    owner = await _save_user(db_session, "owner@example.com")
    other = await _save_user(db_session, "other@example.com")
    repository = new_item_repository(db_session)
    await repository.save(Item.create(owner.id, ItemTitle("Owner item")))
    await repository.save(Item.create(other.id, ItemTitle("Other item")))
    await db_session.commit()

    # Act
    count = await repository.count_by_owner_id(owner.id)

    # Assert
    assert count == 1


async def test_item_repository_finds_items_by_owner(db_session: AsyncSession) -> None:
    # Arrange
    owner = await _save_user(db_session, "owner@example.com")
    other = await _save_user(db_session, "other@example.com")
    repository = new_item_repository(db_session)
    item = Item.create(owner.id, ItemTitle("Owner item"))
    await repository.save(item)
    await repository.save(Item.create(other.id, ItemTitle("Other item")))
    await db_session.commit()

    # Act
    items = await repository.find_by_owner_id(owner.id)

    # Assert
    assert items == [item]


async def test_item_repository_updates_item(db_session: AsyncSession) -> None:
    # Arrange
    owner = await _save_user(db_session, "owner@example.com")
    repository = new_item_repository(db_session)
    item = Item.create(owner.id, ItemTitle("Owner item"))
    await repository.save(item)
    await db_session.commit()
    item.update_content(ItemTitle("Updated"), None)

    # Act
    await repository.save(item)
    await db_session.commit()

    # Assert
    found = await repository.find_by_id(item.id)
    assert found is not None
    assert found.title == ItemTitle("Updated")


async def test_item_repository_deletes_item(db_session: AsyncSession) -> None:
    # Arrange
    owner = await _save_user(db_session, "owner@example.com")
    repository = new_item_repository(db_session)
    item = Item.create(owner.id, ItemTitle("Owner item"))
    await repository.save(item)
    await db_session.commit()

    # Act
    await repository.delete(item.id)
    await db_session.commit()

    # Assert
    assert await repository.find_by_id(item.id) is None
