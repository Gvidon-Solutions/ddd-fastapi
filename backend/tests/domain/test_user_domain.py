"""User domain tests."""

from uuid import UUID

import pytest

from app.domain.user.entities import User
from app.domain.user.exceptions import SuperuserSelfDeletionError
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash, UserId


def test_email_address_validates_required_shape_and_length() -> None:
    with pytest.raises(ValueError, match="Email is required"):
        EmailAddress("")
    with pytest.raises(ValueError, match="local part"):
        EmailAddress("invalid")
    with pytest.raises(ValueError, match="255"):
        EmailAddress(f"{'x' * 256}@example.com")


def test_full_name_and_password_hash_validate_constraints() -> None:
    with pytest.raises(ValueError, match="255"):
        FullName("x" * 256)
    with pytest.raises(ValueError, match="required"):
        PasswordHash("")


def test_user_id_generates_uuid() -> None:
    user_id = UserId.generate()

    assert isinstance(user_id.value, UUID)
    assert str(user_id) == str(user_id.value)


def test_user_equality_uses_identity() -> None:
    user_id = UserId.generate()
    left = User(user_id, EmailAddress("a@example.com"), PasswordHash("hash"))
    right = User(user_id, EmailAddress("b@example.com"), PasswordHash("hash"))

    assert left == right
    assert hash(left) == hash(right)


def test_user_mutators_update_state() -> None:
    user = User.create(EmailAddress("old@example.com"), PasswordHash("hash"))

    user.update_email(EmailAddress("new@example.com"))
    user.update_full_name(FullName("New Name"))
    user.update_password_hash(PasswordHash("new-hash"))
    user.deactivate()
    user.grant_superuser()

    assert user.email == EmailAddress("new@example.com")
    assert user.full_name == FullName("New Name")
    assert user.hashed_password == PasswordHash("new-hash")
    assert not user.is_active
    assert user.is_superuser

    user.activate()
    user.revoke_superuser()

    assert user.is_active
    assert not user.is_superuser


def test_superuser_cannot_delete_self() -> None:
    user = User.create(
        EmailAddress("admin@example.com"),
        PasswordHash("hash"),
        is_superuser=True,
    )

    with pytest.raises(SuperuserSelfDeletionError):
        user.ensure_can_delete_self()
