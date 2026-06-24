"""Filesystem job artifact storage tests."""

from pathlib import Path

import pytest

from app.domain.job import ArtifactLocation, ArtifactLocationType
from app.infrastructure.job_artifact_storage import FilesystemJobArtifactStorage

pytestmark = pytest.mark.anyio


async def test_filesystem_job_artifact_storage_writes_and_reads_bytes(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemJobArtifactStorage(root=tmp_path)

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


async def test_filesystem_job_artifact_storage_writes_path_content(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemJobArtifactStorage(root=tmp_path / "artifacts")
    source_path = tmp_path / "source.md"
    source_path.write_bytes(b"artifact from file")

    # Act
    location = await storage.write(content=source_path)
    content = await storage.read(location)

    # Assert
    assert location.type == ArtifactLocationType.FILESYSTEM
    assert location.uri is not None
    assert Path(location.uri).parent == tmp_path / "artifacts"
    assert Path(location.uri).suffix == ".md"
    assert content == b"artifact from file"


async def test_filesystem_job_artifact_storage_skips_copy_for_stored_path(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemJobArtifactStorage(root=tmp_path / "artifacts")
    original_location = await storage.write(
        content=b"already stored",
        metadata={"filename": "report.txt"},
    )
    assert original_location.uri is not None
    stored_path = Path(original_location.uri)

    # Act
    location = await storage.write(content=stored_path)

    # Assert
    assert location == original_location
    assert list((tmp_path / "artifacts").iterdir()) == [stored_path]


async def test_filesystem_job_artifact_storage_deletes_artifact(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemJobArtifactStorage(root=tmp_path)
    location = await storage.write(content=b"artifact bytes")
    assert location.uri is not None

    # Act
    await storage.delete(location)

    # Assert
    assert not Path(location.uri).exists()
    with pytest.raises(FileNotFoundError):
        await storage.read(location)


async def test_filesystem_job_artifact_storage_rejects_non_filesystem_location(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemJobArtifactStorage(root=tmp_path)

    # Act / Assert
    with pytest.raises(ValueError, match="Unsupported artifact location type"):
        await storage.read(
            ArtifactLocation(
                type=ArtifactLocationType.POSTGRES,
                uri="artifact-id",
            )
        )


async def test_filesystem_job_artifact_storage_rejects_delete_for_non_filesystem_location(
    tmp_path: Path,
) -> None:
    # Arrange
    storage = FilesystemJobArtifactStorage(root=tmp_path)

    # Act / Assert
    with pytest.raises(ValueError, match="Unsupported artifact location type"):
        await storage.delete(
            ArtifactLocation(
                type=ArtifactLocationType.POSTGRES,
                uri="artifact-id",
            )
        )
