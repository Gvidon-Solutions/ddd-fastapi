"""ItemDescription value object tests."""

import pytest

from app.domain.item.value_objects import ItemDescription


def test_item_description_accepts_valid_value() -> None:
    # Arrange
    value = "Description"

    # Act
    description = ItemDescription(value)

    # Assert
    assert description.value == value
    assert str(description) == value


def test_item_description_rejects_long_value() -> None:
    # Arrange
    value = "x" * 256

    # Act / Assert
    with pytest.raises(ValueError, match="255"):
        ItemDescription(value)
