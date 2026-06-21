"""User use case tests."""

import pytest

from app.domain.user.entities import User
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

pytestmark = pytest.mark.anyio


async def test_create_user_hashes_password() -> None:
    # Arrange
    repository = InMemoryUserRepository()
    use_case = new_create_user_use_case(repository, FakePasswordHasher())

    # Act
    user = await use_case.execute(EmailAddress("new@example.com"), "secret")

    # Assert
    assert user.hashed_password == PasswordHash("hashed:secret")


async def test_create_user_persists_user() -> None:
    # Arrange
    repository = InMemoryUserRepository()
    use_case = new_create_user_use_case(repository, FakePasswordHasher())

    # Act
    user = await use_case.execute(EmailAddress("new@example.com"), "secret")

    # Assert
    assert await repository.find_by_email(EmailAddress("new@example.com")) == user


async def test_create_user_rejects_duplicate_email() -> None:
    # Arrange
    repository = InMemoryUserRepository()
    use_case = new_create_user_use_case(repository, FakePasswordHasher())
    await use_case.execute(EmailAddress("new@example.com"), "secret")

    # Act / Assert
    with pytest.raises(EmailAlreadyExistsError):
        await use_case.execute(EmailAddress("new@example.com"), "secret")


async def test_register_user_creates_regular_user() -> None:
    # Arrange
    repository = InMemoryUserRepository()
    use_case = new_register_user_use_case(repository, FakePasswordHasher())

    # Act
    user = await use_case.execute(EmailAddress("new@example.com"), "secret")

    # Assert
    assert not user.is_superuser


async def test_authenticate_user_returns_user(user: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user])
    use_case = new_authenticate_user_use_case(repository, FakePasswordHasher())

    # Act
    result = await use_case.execute(user.email, "secret")

    # Assert
    assert result == user


async def test_authenticate_user_persists_upgraded_password_hash(user: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user])
    use_case = new_authenticate_user_use_case(
        repository,
        FakePasswordHasher(updated_hash=PasswordHash("upgraded")),
    )

    # Act
    await use_case.execute(user.email, "secret")

    # Assert
    persisted_user = await repository.find_by_id(user.id)
    assert persisted_user is not None
    assert persisted_user.hashed_password == PasswordHash("upgraded")


async def test_authenticate_user_rejects_invalid_credentials(user: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user])
    use_case = new_authenticate_user_use_case(
        repository,
        FakePasswordHasher(verified=False),
    )

    # Act / Assert
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(user.email, "bad")


async def test_authenticate_user_rejects_inactive_user(user: User) -> None:
    # Arrange
    user.deactivate()
    repository = InMemoryUserRepository([user])
    use_case = new_authenticate_user_use_case(repository, FakePasswordHasher())

    # Act / Assert
    with pytest.raises(InactiveUserError):
        await use_case.execute(user.email, "secret")


async def test_find_users_returns_users_for_admin(user: User, admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_users_use_case(repository)

    # Act
    result = await use_case.execute(admin)

    # Assert
    assert result.count == 2
    assert result.data == [user, admin]


async def test_find_users_rejects_regular_user(user: User, admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_users_use_case(repository)

    # Act / Assert
    with pytest.raises(UserAccessDeniedError):
        await use_case.execute(user)


async def test_find_user_by_id_returns_current_user(user: User, admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_user_by_id_use_case(repository)

    # Act
    result = await use_case.execute(user.id, user)

    # Assert
    assert result == user


async def test_find_user_by_id_allows_admin(user: User, admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_user_by_id_use_case(repository)

    # Act
    result = await use_case.execute(user.id, admin)

    # Assert
    assert result == user


async def test_find_user_by_id_rejects_other_regular_user(
    user: User, admin: User
) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_find_user_by_id_use_case(repository)

    # Act / Assert
    with pytest.raises(UserAccessDeniedError):
        await use_case.execute(admin.id, user)


async def test_find_user_by_id_raises_not_found(admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([admin])
    use_case = new_find_user_by_id_use_case(repository)

    # Act / Assert
    with pytest.raises(UserNotFoundError):
        await use_case.execute(UserId.generate(), admin)


async def test_update_current_user_updates_full_name(user: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user])
    use_case = new_update_current_user_use_case(repository)

    # Act
    updated = await use_case.execute(user, full_name=FullName("Updated"))

    # Assert
    assert updated.full_name == FullName("Updated")


async def test_update_current_user_rejects_duplicate_email(
    user: User,
    admin: User,
) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_update_current_user_use_case(repository)

    # Act / Assert
    with pytest.raises(EmailAlreadyExistsError):
        await use_case.execute(user, email=admin.email)


async def test_update_current_user_password_rejects_reused_password(user: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user])
    use_case = new_update_current_user_password_use_case(
        repository,
        FakePasswordHasher(),
    )

    # Act / Assert
    with pytest.raises(PasswordReuseError):
        await use_case.execute(user, "same", "same")


async def test_update_current_user_password_rejects_incorrect_current_password(
    user: User,
) -> None:
    # Arrange
    repository = InMemoryUserRepository([user])
    use_case = new_update_current_user_password_use_case(
        repository,
        FakePasswordHasher(verified=False),
    )

    # Act / Assert
    with pytest.raises(IncorrectPasswordError):
        await use_case.execute(user, "old", "new")


async def test_update_user_updates_fields(user: User, admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_update_user_use_case(repository, FakePasswordHasher())

    # Act
    updated = await use_case.execute(
        admin,
        user.id,
        email=EmailAddress("updated@example.com"),
        plain_password="secret",
        is_active=False,
        is_superuser=True,
    )

    # Assert
    assert updated.email == EmailAddress("updated@example.com")
    assert updated.hashed_password == PasswordHash("hashed:secret")
    assert not updated.is_active
    assert updated.is_superuser


async def test_update_user_rejects_regular_user(user: User, admin: User) -> None:
    # Arrange
    user.revoke_superuser()
    repository = InMemoryUserRepository([user, admin])
    use_case = new_update_user_use_case(repository, FakePasswordHasher())

    # Act / Assert
    with pytest.raises(UserAccessDeniedError):
        await use_case.execute(user, admin.id)


async def test_update_user_raises_not_found(admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([admin])
    use_case = new_update_user_use_case(repository, FakePasswordHasher())

    # Act / Assert
    with pytest.raises(UserNotFoundError):
        await use_case.execute(admin, UserId.generate())


async def test_delete_user_rejects_admin_self_delete(admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([admin])
    use_case = new_delete_user_use_case(repository)

    # Act / Assert
    with pytest.raises(SuperuserSelfDeletionError):
        await use_case.execute(admin, admin.id)


async def test_delete_user_removes_user(user: User, admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([user, admin])
    use_case = new_delete_user_use_case(repository)

    # Act
    await use_case.execute(admin, user.id)

    # Assert
    assert await repository.find_by_id(user.id) is None


async def test_delete_current_user_rejects_admin(admin: User) -> None:
    # Arrange
    repository = InMemoryUserRepository([admin])
    use_case = new_delete_current_user_use_case(repository)

    # Act / Assert
    with pytest.raises(SuperuserSelfDeletionError):
        await use_case.execute(admin)
