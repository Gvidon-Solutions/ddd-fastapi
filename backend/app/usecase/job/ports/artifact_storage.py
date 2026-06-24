"""Define the artifact storage port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.domain.job import ArtifactLocation


class ArtifactStorage(ABC):
    """Store and read artifact payload bytes."""

    @abstractmethod
    async def write(
        self,
        content: bytes | Path,
        metadata: dict | None = None,
    ) -> ArtifactLocation:
        """Write bytes or file content and return their storage location."""

    @abstractmethod
    async def read(self, location: ArtifactLocation) -> bytes:
        """Read bytes from a storage location."""

    @abstractmethod
    async def delete(self, location: ArtifactLocation) -> None:
        """Delete artifact payload from a storage location."""
