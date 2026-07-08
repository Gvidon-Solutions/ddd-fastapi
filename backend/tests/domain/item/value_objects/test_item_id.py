"""ItemId value object tests."""

from uuid import UUID

from app.domain.item.value_objects import new_item_id


def test_item_id_generates_uuid() -> None:
    # Act
    item_id = new_item_id()

    # Assert
    assert isinstance(item_id, UUID)
    assert str(item_id) == str(item_id)
