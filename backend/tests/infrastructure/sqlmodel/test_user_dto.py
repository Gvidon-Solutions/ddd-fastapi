"""UserDTO tests."""

from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash
from app.infrastructure.sqlmodel.user import UserDTO


def test_user_dto_uses_user_table_name() -> None:
    # Act
    table_name = UserDTO.__tablename__

    # Assert
    assert table_name == "user"


def test_user_dto_round_trips_entity_identity() -> None:
    # Arrange
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))

    # Act
    entity = UserDTO.from_entity(user).to_entity()

    # Assert
    assert entity == user


def test_user_dto_round_trips_user_fields() -> None:
    # Arrange
    user = User.create(
        EmailAddress("user@example.com"),
        PasswordHash("hash"),
        FullName("User"),
        is_superuser=True,
    )

    # Act
    entity = UserDTO.from_entity(user).to_entity()

    # Assert
    assert entity.email == user.email
    assert entity.full_name == user.full_name
    assert entity.hashed_password == user.hashed_password
    assert entity.is_superuser
