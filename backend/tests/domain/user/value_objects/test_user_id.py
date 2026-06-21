"""UserId value object tests."""

from uuid import UUID

from app.domain.user.value_objects import UserId


def test_user_id_generates_uuid() -> None:
    # Act
    user_id = UserId.generate()

    # Assert
    assert isinstance(user_id.value, UUID)
    assert str(user_id) == str(user_id.value)
