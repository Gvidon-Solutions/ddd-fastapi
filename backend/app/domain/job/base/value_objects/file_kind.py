"""Define file kinds."""

from __future__ import annotations

from enum import StrEnum


class FileKind(StrEnum):
    """Represent stored file content kinds."""

    FILE = "file"
    TEXT = "text"
