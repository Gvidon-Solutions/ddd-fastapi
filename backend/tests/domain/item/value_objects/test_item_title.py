"""ItemTitle value object tests."""

import pytest

from app.domain.item.value_objects import ItemTitle


def test_item_title_accepts_valid_value() -> None:
    # Arrange
    value = "Title"

    # Act
    title = ItemTitle(value)

    # Assert
    assert title.value == value
    assert str(title) == value


def test_item_title_rejects_empty_value() -> None:
    # Arrange
    value = ""

    # Act / Assert
    with pytest.raises(ValueError, match="Title is required"):
        ItemTitle(value)


def test_item_title_rejects_long_value() -> None:
    # Arrange
    value = "x" * 256

    # Act / Assert
    with pytest.raises(ValueError, match="255"):
        ItemTitle(value)
