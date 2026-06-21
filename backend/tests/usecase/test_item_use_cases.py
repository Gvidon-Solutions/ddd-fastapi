"""Item use case tests."""

import pytest

from app.domain.item.entities import Item
from app.domain.item.exceptions import ItemAccessDeniedError, ItemNotFoundError
from app.domain.item.value_objects import ItemDescription, ItemId, ItemTitle
from app.domain.user.entities import User
from app.usecase.item import (
    new_create_item_use_case,
    new_delete_item_use_case,
    new_find_item_by_id_use_case,
    new_find_items_use_case,
    new_update_item_use_case,
)
from tests.usecase.fakes import InMemoryItemRepository

pytestmark = pytest.mark.anyio


async def test_create_item_persists_item(user: User) -> None:
    # Arrange
    repository = InMemoryItemRepository()
    use_case = new_create_item_use_case(repository)

    # Act
    item = await use_case.execute(user, ItemTitle("Title"), ItemDescription("Body"))

    # Assert
    assert await repository.find_by_id(item.id) == item
    assert item.owner_id == user.id


async def test_find_items_returns_only_owned_items_for_regular_user(
    user: User,
    admin: User,
    item: Item,
) -> None:
    # Arrange
    admin_item = Item.create(admin.id, ItemTitle("Admin item"))
    repository = InMemoryItemRepository([item, admin_item])
    use_case = new_find_items_use_case(repository)

    # Act
    result = await use_case.execute(user)

    # Assert
    assert result.data == [item]
    assert result.count == 1


async def test_find_items_returns_all_items_for_admin(
    admin: User,
    item: Item,
) -> None:
    # Arrange
    admin_item = Item.create(admin.id, ItemTitle("Admin item"))
    repository = InMemoryItemRepository([item, admin_item])
    use_case = new_find_items_use_case(repository)

    # Act
    result = await use_case.execute(admin)

    # Assert
    assert result.count == 2
    assert result.data == [item, admin_item]


async def test_find_item_by_id_returns_owned_item(user: User, item: Item) -> None:
    # Arrange
    repository = InMemoryItemRepository([item])
    use_case = new_find_item_by_id_use_case(repository)

    # Act
    result = await use_case.execute(user, item.id)

    # Assert
    assert result == item


async def test_find_item_by_id_allows_admin_access(admin: User, item: Item) -> None:
    # Arrange
    repository = InMemoryItemRepository([item])
    use_case = new_find_item_by_id_use_case(repository)

    # Act
    result = await use_case.execute(admin, item.id)

    # Assert
    assert result == item


async def test_find_item_by_id_rejects_other_regular_user(
    admin: User,
    item: Item,
) -> None:
    # Arrange
    admin.revoke_superuser()
    repository = InMemoryItemRepository([item])
    use_case = new_find_item_by_id_use_case(repository)

    # Act / Assert
    with pytest.raises(ItemAccessDeniedError):
        await use_case.execute(admin, item.id)


async def test_find_item_by_id_raises_not_found(user: User) -> None:
    # Arrange
    use_case = new_find_item_by_id_use_case(InMemoryItemRepository())

    # Act / Assert
    with pytest.raises(ItemNotFoundError):
        await use_case.execute(user, ItemId.generate())


async def test_update_item_updates_owned_item(user: User, item: Item) -> None:
    # Arrange
    repository = InMemoryItemRepository([item])
    use_case = new_update_item_use_case(repository)

    # Act
    updated = await use_case.execute(
        user,
        item.id,
        ItemTitle("Updated"),
        ItemDescription("Updated body"),
    )

    # Assert
    assert updated.title == ItemTitle("Updated")
    assert updated.description == ItemDescription("Updated body")
    assert await repository.find_by_id(item.id) == updated


async def test_delete_item_removes_owned_item(user: User, item: Item) -> None:
    # Arrange
    repository = InMemoryItemRepository([item])
    use_case = new_delete_item_use_case(repository)

    # Act
    await use_case.execute(user, item.id)

    # Assert
    assert await repository.find_by_id(item.id) is None
