"""Define the File identifier type."""

from typing import NewType
from uuid import UUID, uuid4

FileId = NewType("FileId", UUID)


def new_file_id() -> FileId:
    """Generate a new identifier for a file."""
    return FileId(uuid4())
