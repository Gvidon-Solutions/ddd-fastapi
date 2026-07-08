"""UserId value object tests."""

from uuid import UUID

from app.domain.user.value_objects import new_user_id


def test_user_id_generates_uuid() -> None:
    # Act
    user_id = new_user_id()

    # Assert
    assert isinstance(user_id, UUID)
    assert str(user_id) == str(user_id)
