"""ItemId value object tests."""

from uuid import UUID

from app.domain.item.value_objects import ItemId


def test_item_id_generates_uuid() -> None:
    # Act
    item_id = ItemId.generate()

    # Assert
    assert isinstance(item_id.value, UUID)
    assert str(item_id) == str(item_id.value)
