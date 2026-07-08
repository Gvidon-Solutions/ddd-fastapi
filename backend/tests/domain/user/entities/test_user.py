"""User entity tests."""

import pytest

from app.domain.user.entities import User
from app.domain.user.exceptions import SuperuserSelfDeletionError
from app.domain.user.value_objects import (
    EmailAddress,
    FullName,
    PasswordHash,
    new_user_id,
)


def test_user_create_generates_regular_active_user() -> None:
    # Arrange
    email = EmailAddress("user@example.com")
    hashed_password = PasswordHash("hash")
    full_name = FullName("User Name")

    # Act
    user = User.create(email, hashed_password, full_name)

    # Assert
    assert user.email == email
    assert user.hashed_password == hashed_password
    assert user.full_name == full_name
    assert user.is_active
    assert not user.is_superuser


def test_user_create_can_create_superuser() -> None:
    # Arrange
    email = EmailAddress("admin@example.com")
    hashed_password = PasswordHash("hash")

    # Act
    user = User.create(email, hashed_password, is_superuser=True)

    # Assert
    assert user.is_superuser


def test_user_equality_uses_identity() -> None:
    # Arrange
    user_id = new_user_id()
    left = User(user_id, EmailAddress("a@example.com"), PasswordHash("hash"))
    right = User(user_id, EmailAddress("b@example.com"), PasswordHash("hash"))

    # Act
    users_are_equal = left == right

    # Assert
    assert users_are_equal
    assert hash(left) == hash(right)


def test_user_update_email_replaces_email() -> None:
    # Arrange
    user = User.create(EmailAddress("old@example.com"), PasswordHash("hash"))
    new_email = EmailAddress("new@example.com")

    # Act
    user.update_email(new_email)

    # Assert
    assert user.email == new_email


def test_user_update_full_name_replaces_full_name() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))
    full_name = FullName("New Name")

    # Act
    user.update_full_name(full_name)

    # Assert
    assert user.full_name == full_name


def test_user_update_password_hash_replaces_hash() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))
    password_hash = PasswordHash("new-hash")

    # Act
    user.update_password_hash(password_hash)

    # Assert
    assert user.hashed_password == password_hash


def test_user_deactivate_marks_user_inactive() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))

    # Act
    user.deactivate()

    # Assert
    assert not user.is_active


def test_user_activate_marks_user_active() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))
    user.deactivate()

    # Act
    user.activate()

    # Assert
    assert user.is_active


def test_user_grant_superuser_marks_user_as_superuser() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))

    # Act
    user.grant_superuser()

    # Assert
    assert user.is_superuser


def test_user_revoke_superuser_removes_superuser_flag() -> None:
    # Arrange
    user = User.create(
        EmailAddress("admin@example.com"),
        PasswordHash("hash"),
        is_superuser=True,
    )

    # Act
    user.revoke_superuser()

    # Assert
    assert not user.is_superuser


def test_regular_user_can_delete_self() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))

    # Act
    user.ensure_can_delete_self()

    # Assert
    assert not user.is_superuser


def test_superuser_cannot_delete_self() -> None:
    # Arrange
    user = User.create(
        EmailAddress("admin@example.com"),
        PasswordHash("hash"),
        is_superuser=True,
    )

    # Act / Assert
    with pytest.raises(SuperuserSelfDeletionError):
        user.ensure_can_delete_self()
