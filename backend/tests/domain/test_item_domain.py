"""Item domain tests."""

from uuid import UUID

import pytest

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemId, ItemTitle
from app.domain.user.value_objects import UserId


def test_item_title_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="Title is required"):
        ItemTitle("")


def test_item_title_rejects_long_value() -> None:
    with pytest.raises(ValueError, match="255"):
        ItemTitle("x" * 256)


def test_item_description_rejects_long_value() -> None:
    with pytest.raises(ValueError, match="255"):
        ItemDescription("x" * 256)


def test_item_id_generates_uuid() -> None:
    item_id = ItemId.generate()

    assert isinstance(item_id.value, UUID)
    assert str(item_id) == str(item_id.value)


def test_item_equality_uses_identity() -> None:
    item_id = ItemId.generate()
    owner_id = UserId.generate()
    left = Item(item_id, owner_id, ItemTitle("A"))
    right = Item(item_id, owner_id, ItemTitle("B"))

    assert left == right
    assert hash(left) == hash(right)


def test_item_create_update_and_ownership() -> None:
    owner_id = UserId.generate()
    item = Item.create(owner_id, ItemTitle("Initial"))

    assert item.is_owned_by(owner_id)

    item.update_content(ItemTitle("Updated"), ItemDescription("Body"))

    assert item.title == ItemTitle("Updated")
    assert item.description == ItemDescription("Body")
