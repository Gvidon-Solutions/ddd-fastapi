"""EmailAddress value object tests."""

import pytest

from app.domain.user.value_objects import EmailAddress


def test_email_address_accepts_valid_email() -> None:
    # Arrange
    value = "user@example.com"

    # Act
    email = EmailAddress(value)

    # Assert
    assert email.value == value
    assert str(email) == value


def test_email_address_rejects_empty_value() -> None:
    # Arrange
    value = ""

    # Act / Assert
    with pytest.raises(ValueError, match="Email is required"):
        EmailAddress(value)


def test_email_address_rejects_invalid_shape() -> None:
    # Arrange
    value = "invalid"

    # Act / Assert
    with pytest.raises(ValueError, match="local part"):
        EmailAddress(value)


def test_email_address_rejects_long_value() -> None:
    # Arrange
    value = f"{'x' * 256}@example.com"

    # Act / Assert
    with pytest.raises(ValueError, match="255"):
        EmailAddress(value)
