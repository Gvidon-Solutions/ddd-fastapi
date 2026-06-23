"""Define artifact location types."""

from __future__ import annotations

from enum import StrEnum


class ArtifactLocationType(StrEnum):
    """Represent where an artifact payload is stored."""

    INLINE = "inline"
    POSTGRES = "postgres"
    S3 = "s3"
    FILESYSTEM = "filesystem"
