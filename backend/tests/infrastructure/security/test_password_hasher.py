"""Password hasher tests."""

from app.infrastructure.security import new_password_hasher


def test_password_hasher_hashes_password() -> None:
    # Arrange
    hasher = new_password_hasher()

    # Act
    hashed = hasher.hash_password("secret")

    # Assert
    assert hashed.value != "secret"


def test_password_hasher_verifies_password() -> None:
    # Arrange
    hasher = new_password_hasher()
    hashed = hasher.hash_password("secret")

    # Act
    result = hasher.verify_password("secret", hashed)

    # Assert
    assert result.verified


def test_password_hasher_rejects_wrong_password() -> None:
    # Arrange
    hasher = new_password_hasher()
    hashed = hasher.hash_password("secret")

    # Act
    result = hasher.verify_password("wrong", hashed)

    # Assert
    assert not result.verified
