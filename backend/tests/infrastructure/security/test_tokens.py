"""Security token tests."""

from datetime import timedelta

from app.infrastructure.security import (
    create_access_token,
    generate_password_reset_token,
    verify_password_reset_token,
)


def test_create_access_token_returns_token() -> None:
    # Act
    access_token = create_access_token("subject", timedelta(minutes=1))

    # Assert
    assert access_token


def test_password_reset_token_round_trips_email() -> None:
    # Arrange
    email = "user@example.com"

    # Act
    token = generate_password_reset_token(email)

    # Assert
    assert verify_password_reset_token(token) == email


def test_password_reset_token_rejects_invalid_token() -> None:
    # Arrange
    token = "invalid"

    # Act
    email = verify_password_reset_token(token)

    # Assert
    assert email is None
