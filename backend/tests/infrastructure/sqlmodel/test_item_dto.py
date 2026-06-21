"""ItemDTO tests."""

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.entities import User
from app.infrastructure.sqlmodel.item import ItemDTO


def test_item_dto_uses_item_table_name() -> None:
    # Act
    table_name = ItemDTO.__tablename__

    # Assert
    assert table_name == "item"


def test_item_dto_round_trips_entity_identity(user: User) -> None:
    # Arrange
    item = Item.create(user.id, ItemTitle("Item"))

    # Act
    entity = ItemDTO.from_entity(item).to_entity()

    # Assert
    assert entity == item


def test_item_dto_round_trips_item_fields(user: User) -> None:
    # Arrange
    item = Item.create(
        user.id,
        ItemTitle("Item"),
        ItemDescription("Description"),
    )

    # Act
    entity = ItemDTO.from_entity(item).to_entity()

    # Assert
    assert entity.owner_id == user.id
    assert entity.title == item.title
    assert entity.description == item.description
