"""Filesystem job artifact storage."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.domain.job import ArtifactLocation, ArtifactLocationType
from app.usecase.job.ports import ArtifactStorage


class FilesystemJobArtifactStorage(ArtifactStorage):
    """Store artifact payloads on the local filesystem."""

    def __init__(self, root: Path | str = settings.JOB_ARTIFACT_STORAGE_DIRECTORY):
        """Store the root directory for artifact payloads."""
        self.root = Path(root)

    async def write(
        self,
        content: bytes | Path,
        metadata: dict | None = None,
    ) -> ArtifactLocation:
        """Write bytes or file content to the filesystem and return their location."""
        self.root.mkdir(parents=True, exist_ok=True)
        if isinstance(content, Path) and self._is_stored_path(content):
            return ArtifactLocation(
                type=ArtifactLocationType.FILESYSTEM,
                uri=str(content),
            )
        content_bytes, source_path = self._content_bytes(content)
        filename = self._build_filename(metadata, source_path)
        path = self.root / filename
        path.write_bytes(content_bytes)
        return ArtifactLocation(
            type=ArtifactLocationType.FILESYSTEM,
            uri=str(path),
        )

    async def read(self, location: ArtifactLocation) -> bytes:
        """Read bytes from a filesystem artifact location."""
        path = self._path(location)
        if not path.is_file():
            raise FileNotFoundError(location.uri)
        return path.read_bytes()

    async def delete(self, location: ArtifactLocation) -> None:
        """Delete bytes from a filesystem artifact location."""
        path = self._path(location)
        if not path.is_file():
            raise FileNotFoundError(location.uri)
        path.unlink()

    def _content_bytes(self, content: bytes | Path) -> tuple[bytes, Path | None]:
        """Return bytes and optional source path for stored content."""
        if isinstance(content, bytes):
            return content, None
        if isinstance(content, Path):
            return content.read_bytes(), content
        raise TypeError(f"Unsupported artifact content type: {type(content).__name__}")

    def _build_filename(
        self,
        metadata: dict | None,
        source_path: Path | None = None,
    ) -> str:
        """Build a safe storage filename."""
        suffix = ""
        if metadata is not None:
            original_filename = metadata.get("filename")
            if isinstance(original_filename, str):
                suffix = Path(original_filename).suffix
        if not suffix and source_path is not None:
            suffix = source_path.suffix
        return f"{uuid4()}{suffix}"

    def _is_stored_path(self, path: Path) -> bool:
        """Return whether a file already lives under this storage root."""
        if not path.is_file():
            return False
        return path.resolve().is_relative_to(self.root.resolve())

    def _path(self, location: ArtifactLocation) -> Path:
        """Return a filesystem path for an artifact location."""
        if location.type != ArtifactLocationType.FILESYSTEM:
            raise ValueError(f"Unsupported artifact location type: {location.type}")
        if location.uri is None:
            raise ValueError("Filesystem artifact location requires uri")
        return Path(location.uri)


def new_filesystem_job_artifact_storage() -> ArtifactStorage:
    """Create filesystem-backed job artifact storage."""
    return FilesystemJobArtifactStorage()
