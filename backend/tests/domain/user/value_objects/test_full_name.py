"""FullName value object tests."""

import pytest

from app.domain.user.value_objects import FullName


def test_full_name_accepts_valid_value() -> None:
    # Arrange
    value = "User Name"

    # Act
    full_name = FullName(value)

    # Assert
    assert full_name.value == value
    assert str(full_name) == value


def test_full_name_rejects_long_value() -> None:
    # Arrange
    value = "x" * 256

    # Act / Assert
    with pytest.raises(ValueError, match="255"):
        FullName(value)
