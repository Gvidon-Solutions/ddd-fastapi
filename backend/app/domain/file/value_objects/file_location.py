"""Define the FileLocation value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileLocation:
    """Represent a pointer to stored file content."""

    uri: str
