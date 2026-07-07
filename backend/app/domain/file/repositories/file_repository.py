"""Define the File repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.file.entities import File


class FileRepository(ABC):
    """Persist file metadata."""

    @abstractmethod
    async def create(self, file: File) -> None:
        """Create file metadata."""

    @abstractmethod
    async def get(self, file_id: UUID) -> File:
        """Return file metadata."""
