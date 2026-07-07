"""Define the File repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.file.entities import File
from app.domain.file.value_objects import FileId


class FileRepository(ABC):
    """Persist file metadata."""

    @abstractmethod
    async def create(self, file: File) -> None:
        """Create file metadata."""

    @abstractmethod
    async def get(self, file_id: FileId) -> File:
        """Return file metadata."""
