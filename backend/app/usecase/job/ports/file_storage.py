"""Define the file storage port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.domain.job import FileLocation


class FileStorage(ABC):
    """Store and read file payload bytes."""

    @abstractmethod
    async def write(
        self,
        content: bytes | Path,
        metadata: dict | None = None,
    ) -> FileLocation:
        """Write bytes or file content and return their storage location."""

    @abstractmethod
    async def read(self, location: FileLocation) -> bytes:
        """Read bytes from a storage location."""

    @abstractmethod
    async def delete(self, location: FileLocation) -> None:
        """Delete payload from a storage location."""
