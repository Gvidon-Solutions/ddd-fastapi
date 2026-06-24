"""Define artifact kinds."""

from __future__ import annotations

from enum import StrEnum


class ArtifactKind(StrEnum):
    """Represent the shape of an artifact payload."""

    JSON = "json"
    TEXT = "text"
    FILE = "file"
    TABLE = "table"
