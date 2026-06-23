"""Filesystem artifact storage."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.domain.job import ArtifactLocation, ArtifactLocationType
from app.usecase.job import ArtifactStorage


class FilesystemArtifactStorage(ArtifactStorage):
    """Store artifact payloads on the local filesystem."""

    def __init__(self, root: Path | str = settings.JOB_ARTIFACT_STORAGE_DIRECTORY):
        """Store the root directory for artifact payloads."""
        self.root = Path(root)

    async def write(
        self,
        content: bytes,
        metadata: dict | None = None,
    ) -> ArtifactLocation:
        """Write bytes to the filesystem and return their location."""
        self.root.mkdir(parents=True, exist_ok=True)
        filename = self._build_filename(metadata)
        path = self.root / filename
        path.write_bytes(content)
        return ArtifactLocation(
            type=ArtifactLocationType.FILESYSTEM,
            uri=str(path),
        )

    async def read(self, location: ArtifactLocation) -> bytes:
        """Read bytes from a filesystem artifact location."""
        if location.type != ArtifactLocationType.FILESYSTEM:
            raise ValueError(f"Unsupported artifact location type: {location.type}")
        if location.uri is None:
            raise ValueError("Filesystem artifact location requires uri")
        path = Path(location.uri)
        if not path.is_file():
            raise FileNotFoundError(location.uri)
        return path.read_bytes()

    def _build_filename(self, metadata: dict | None) -> str:
        """Build a safe storage filename."""
        suffix = ""
        if metadata is not None:
            original_filename = metadata.get("filename")
            if isinstance(original_filename, str):
                suffix = Path(original_filename).suffix
        return f"{uuid4()}{suffix}"


def new_filesystem_artifact_storage() -> ArtifactStorage:
    """Create filesystem-backed artifact storage."""
    return FilesystemArtifactStorage()
