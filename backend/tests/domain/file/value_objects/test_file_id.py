"""FileId value object tests."""

from uuid import UUID

from app.domain.file import FileId


def test_file_id_generates_uuid() -> None:
    # Act
    file_id = FileId.generate()

    # Assert
    assert isinstance(file_id.value, UUID)
    assert str(file_id) == str(file_id.value)
