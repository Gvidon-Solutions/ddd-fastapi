"""Define file location types."""

from __future__ import annotations

from enum import StrEnum


class FileLocationType(StrEnum):
    """Represent where file content is stored."""

    FILESYSTEM = "filesystem"
