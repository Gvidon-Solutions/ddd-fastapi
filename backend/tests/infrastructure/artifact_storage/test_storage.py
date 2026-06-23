"""Filesystem artifact storage tests."""

from pathlib import Path

import pytest

from app.domain.job import ArtifactLocation, ArtifactLocationType
from app.infrastructure.artifact_storage import FilesystemArtifactStorage

pytestmark = pytest.mark.anyio


async def test_filesystem_artifact_storage_writes_and_reads_bytes(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemArtifactStorage(root=tmp_path)

    # Act
    location = await storage.write(
        content=b"artifact bytes",
        metadata={"filename": "report.txt"},
    )
    content = await storage.read(location)

    # Assert
    assert location.type == ArtifactLocationType.FILESYSTEM
    assert location.uri is not None
    assert Path(location.uri).parent == tmp_path
    assert Path(location.uri).suffix == ".txt"
    assert content == b"artifact bytes"


async def test_filesystem_artifact_storage_rejects_non_filesystem_location(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemArtifactStorage(root=tmp_path)

    # Act / Assert
    with pytest.raises(ValueError, match="Unsupported artifact location type"):
        await storage.read(
            ArtifactLocation(
                type=ArtifactLocationType.POSTGRES,
                uri="artifact-id",
            )
        )
