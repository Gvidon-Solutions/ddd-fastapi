"""Filesystem file storage tests."""

from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from app.domain.file import FileLocation
from app.infrastructure.file_storage import FilesystemFileStorage

pytestmark = pytest.mark.anyio


async def test_filesystem_file_storage_writes_and_reads_bytes(
    tmp_path: Path,
) -> None:
    storage = FilesystemFileStorage(root=tmp_path)

    location = await storage.write(
        content=b"file bytes",
        metadata={"filename": "report.txt"},
    )
    content = await storage.read(location)

    assert urlparse(location.uri).scheme == "file"
    assert _path(location).parent == tmp_path
    assert _path(location).suffix == ".txt"
    assert content == b"file bytes"


async def test_filesystem_file_storage_writes_path_content(
    tmp_path: Path,
) -> None:
    storage = FilesystemFileStorage(root=tmp_path / "files")
    source_path = tmp_path / "source.md"
    source_path.write_bytes(b"file from path")

    location = await storage.write(content=source_path)
    content = await storage.read(location)

    assert urlparse(location.uri).scheme == "file"
    assert _path(location).parent == tmp_path / "files"
    assert _path(location).suffix == ".md"
    assert content == b"file from path"


async def test_filesystem_file_storage_skips_copy_for_stored_path(
    tmp_path: Path,
) -> None:
    storage = FilesystemFileStorage(root=tmp_path / "files")
    original_location = await storage.write(
        content=b"already stored",
        metadata={"filename": "report.txt"},
    )
    stored_path = _path(original_location)

    location = await storage.write(content=stored_path)

    assert location == original_location
    assert list((tmp_path / "files").iterdir()) == [stored_path]


async def test_filesystem_file_storage_deletes_file(tmp_path: Path) -> None:
    storage = FilesystemFileStorage(root=tmp_path)
    location = await storage.write(content=b"file bytes")

    await storage.delete(location)

    assert not _path(location).exists()
    with pytest.raises(FileNotFoundError):
        await storage.read(location)


async def test_filesystem_file_storage_rejects_non_filesystem_location(
    tmp_path: Path,
) -> None:
    storage = FilesystemFileStorage(root=tmp_path)

    with pytest.raises(ValueError, match="Unsupported file location URI"):
        await storage.read(
            FileLocation(
                uri="postgres://file-id",
            )
        )


async def test_filesystem_file_storage_rejects_delete_for_non_filesystem_location(
    tmp_path: Path,
) -> None:
    storage = FilesystemFileStorage(root=tmp_path)

    with pytest.raises(ValueError, match="Unsupported file location URI"):
        await storage.delete(
            FileLocation(
                uri="postgres://file-id",
            )
        )


def _path(location: FileLocation) -> Path:
    parsed = urlparse(location.uri)
    return Path(unquote(parsed.path))
