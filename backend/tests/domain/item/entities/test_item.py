"""Item entity tests."""

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.value_objects import UserId


def test_item_create_generates_item_for_owner() -> None:
    # Arrange
    owner_id = UserId.generate()
    title = ItemTitle("Title")
    description = ItemDescription("Body")

    # Act
    item = Item.create(owner_id, title, description)

    # Assert
    assert item.owner_id == owner_id
    assert item.title == title
    assert item.description == description


def test_item_equality_uses_identity() -> None:
    # Arrange
    item_id = Item.create(UserId.generate(), ItemTitle("A")).id
    owner_id = UserId.generate()
    left = Item(item_id, owner_id, ItemTitle("A"))
    right = Item(item_id, owner_id, ItemTitle("B"))

    # Act
    items_are_equal = left == right

    # Assert
    assert items_are_equal
    assert hash(left) == hash(right)


def test_item_update_content_replaces_title() -> None:
    # Arrange
    item = Item.create(UserId.generate(), ItemTitle("Initial"))
    title = ItemTitle("Updated")

    # Act
    item.update_content(title)

    # Assert
    assert item.title == title


def test_item_update_content_replaces_description() -> None:
    # Arrange
    item = Item.create(UserId.generate(), ItemTitle("Initial"))
    description = ItemDescription("Updated body")

    # Act
    item.update_content(ItemTitle("Updated"), description)

    # Assert
    assert item.description == description


def test_item_is_owned_by_returns_true_for_owner() -> None:
    # Arrange
    owner_id = UserId.generate()
    item = Item.create(owner_id, ItemTitle("Title"))

    # Act
    is_owned_by_owner = item.is_owned_by(owner_id)

    # Assert
    assert is_owned_by_owner


def test_item_is_owned_by_returns_false_for_other_user() -> None:
    # Arrange
    item = Item.create(UserId.generate(), ItemTitle("Title"))

    # Act
    is_owned_by_other_user = item.is_owned_by(UserId.generate())

    # Assert
    assert not is_owned_by_other_user
