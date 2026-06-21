"""User use case tests."""

import pytest

from app.domain.user.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    PasswordReuseError,
    SuperuserSelfDeletionError,
    UserAccessDeniedError,
    UserNotFoundError,
)
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash, UserId
from app.usecase.user import (
    new_authenticate_user_use_case,
    new_create_user_use_case,
    new_delete_current_user_use_case,
    new_delete_user_use_case,
    new_find_user_by_id_use_case,
    new_find_users_use_case,
    new_register_user_use_case,
    new_update_current_user_password_use_case,
    new_update_current_user_use_case,
    new_update_user_use_case,
)
from tests.usecase.fakes import FakePasswordHasher, InMemoryUserRepository


def test_create_user_hashes_password_and_checks_duplicates() -> None:
    repository = InMemoryUserRepository()
    use_case = new_create_user_use_case(repository, FakePasswordHasher())

    user = use_case.execute(EmailAddress("new@example.com"), "secret")

    assert user.hashed_password == PasswordHash("hashed:secret")
    assert repository.find_by_email(EmailAddress("new@example.com")) == user

    with pytest.raises(EmailAlreadyExistsError):
        use_case.execute(EmailAddress("new@example.com"), "secret")


def test_register_user_creates_regular_user() -> None:
    repository = InMemoryUserRepository()
    use_case = new_register_user_use_case(repository, FakePasswordHasher())

    user = use_case.execute(EmailAddress("new@example.com"), "secret")

    assert not user.is_superuser


def test_authenticate_user_verifies_password_and_updates_hash(user) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user])
    use_case = new_authenticate_user_use_case(
        repository,
        FakePasswordHasher(updated_hash=PasswordHash("upgraded")),
    )

    result = use_case.execute(user.email, "secret")

    assert result == user
    assert repository.find_by_id(user.id).hashed_password == PasswordHash("upgraded")  # type: ignore[union-attr]


def test_authenticate_user_rejects_invalid_or_inactive_user(user) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user])

    with pytest.raises(InvalidCredentialsError):
        new_authenticate_user_use_case(repository, FakePasswordHasher(False)).execute(
            user.email,
            "bad",
        )

    user.deactivate()
    with pytest.raises(InactiveUserError):
        new_authenticate_user_use_case(repository, FakePasswordHasher()).execute(
            user.email,
            "secret",
        )


def test_find_users_requires_admin(user, admin) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_users_use_case(repository)

    result = use_case.execute(admin)

    assert result.count == 2
    with pytest.raises(UserAccessDeniedError):
        use_case.execute(user)


def test_find_user_by_id_enforces_visibility(user, admin) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_user_by_id_use_case(repository)

    assert use_case.execute(user.id, user) == user
    assert use_case.execute(user.id, admin) == user

    with pytest.raises(UserAccessDeniedError):
        use_case.execute(admin.id, user)
    with pytest.raises(UserNotFoundError):
        use_case.execute(UserId.generate(), admin)


def test_update_current_user_checks_duplicate_email(user, admin) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user, admin])
    use_case = new_update_current_user_use_case(repository)

    updated = use_case.execute(user, full_name=FullName("Updated"))

    assert updated.full_name == FullName("Updated")
    with pytest.raises(EmailAlreadyExistsError):
        use_case.execute(user, email=admin.email)


def test_update_current_user_password_checks_current_and_reuse(user) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user])

    with pytest.raises(PasswordReuseError):
        new_update_current_user_password_use_case(
            repository,
            FakePasswordHasher(),
        ).execute(user, "same", "same")

    with pytest.raises(IncorrectPasswordError):
        new_update_current_user_password_use_case(
            repository,
            FakePasswordHasher(False),
        ).execute(user, "old", "new")


def test_update_user_requires_admin_and_updates_fields(user, admin) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user, admin])
    use_case = new_update_user_use_case(repository, FakePasswordHasher())

    updated = use_case.execute(
        admin,
        user.id,
        email=EmailAddress("updated@example.com"),
        plain_password="secret",
        is_active=False,
        is_superuser=True,
    )

    assert updated.email == EmailAddress("updated@example.com")
    assert updated.hashed_password == PasswordHash("hashed:secret")
    assert not updated.is_active
    assert updated.is_superuser

    user.revoke_superuser()
    with pytest.raises(UserAccessDeniedError):
        use_case.execute(user, admin.id)
    with pytest.raises(UserNotFoundError):
        use_case.execute(admin, UserId.generate())


def test_delete_user_and_current_user_rules(user, admin) -> None:  # type: ignore[no-untyped-def]
    repository = InMemoryUserRepository([user, admin])

    with pytest.raises(SuperuserSelfDeletionError):
        new_delete_user_use_case(repository).execute(admin, admin.id)

    new_delete_user_use_case(repository).execute(admin, user.id)
    assert repository.find_by_id(user.id) is None

    with pytest.raises(SuperuserSelfDeletionError):
        new_delete_current_user_use_case(repository).execute(admin)
