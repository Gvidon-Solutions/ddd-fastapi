"""Item use case tests."""

import pytest

from app.domain.item.exceptions import ItemAccessDeniedError, ItemNotFoundError
from app.domain.item.value_objects import ItemDescription, ItemId, ItemTitle
from app.usecase.item import (
    new_create_item_use_case,
    new_delete_item_use_case,
    new_find_item_by_id_use_case,
    new_find_items_use_case,
    new_update_item_use_case,
)
from tests.usecase.fakes import InMemoryItemRepository


def test_create_item_persists_item(user) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryItemRepository()
    use_case = new_create_item_use_case(repository)

    item = use_case.execute(user, ItemTitle("Title"), ItemDescription("Body"))

    assert repository.find_by_id(item.id) == item
    assert item.owner_id == user.id


def test_find_items_filters_by_owner_for_regular_users(user, admin, item) -> None:  # type: ignore[no-untyped-def]
    admin_item = new_create_item_use_case(InMemoryItemRepository()).execute(
        admin,
        ItemTitle("Admin item"),
    )
    repository = InMemoryItemRepository([item, admin_item])
    use_case = new_find_items_use_case(repository)

    regular_result = use_case.execute(user)
    admin_result = use_case.execute(admin)

    assert regular_result.data == [item]
    assert regular_result.count == 1
    assert admin_result.count == 2


def test_find_item_by_id_enforces_access(user, admin, item) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryItemRepository([item])
    use_case = new_find_item_by_id_use_case(repository)

    assert use_case.execute(user, item.id) == item
    assert use_case.execute(admin, item.id) == item

    other_user = admin
    other_user.revoke_superuser()
    with pytest.raises(ItemAccessDeniedError):
        use_case.execute(other_user, item.id)


def test_find_item_by_id_raises_not_found(user) -> None:  # type: ignore[no-untyped-def]
    use_case = new_find_item_by_id_use_case(InMemoryItemRepository())

    with pytest.raises(ItemNotFoundError):
        use_case.execute(user, ItemId.generate())


def test_update_item_updates_owned_item(user, item) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryItemRepository([item])
    use_case = new_update_item_use_case(repository)

    updated = use_case.execute(
        user,
        item.id,
        ItemTitle("Updated"),
        ItemDescription("Updated body"),
    )

    assert updated.title == ItemTitle("Updated")
    assert repository.find_by_id(item.id) == updated


def test_delete_item_removes_owned_item(user, item) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryItemRepository([item])
    use_case = new_delete_item_use_case(repository)

    use_case.execute(user, item.id)

    assert repository.find_by_id(item.id) is None
