"""FileId value object tests."""

from uuid import UUID

from app.domain.file import new_file_id


def test_file_id_generates_uuid() -> None:
    # Act
    file_id = new_file_id()

    # Assert
    assert isinstance(file_id, UUID)
    assert str(file_id) == str(file_id)
