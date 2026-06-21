"""PasswordHash value object tests."""

import pytest

from app.domain.user.value_objects import PasswordHash


def test_password_hash_accepts_valid_value() -> None:
    # Arrange
    value = "hash"

    # Act
    password_hash = PasswordHash(value)

    # Assert
    assert password_hash.value == value
    assert str(password_hash) == value


def test_password_hash_rejects_empty_value() -> None:
    # Arrange
    value = ""

    # Act / Assert
    with pytest.raises(ValueError, match="required"):
        PasswordHash(value)
