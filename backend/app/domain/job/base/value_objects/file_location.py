"""Define the FileLocation value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.value_objects.file_location_type import FileLocationType


@dataclass(frozen=True)
class FileLocation:
    """Represent a pointer to stored file content."""

    type: FileLocationType
    uri: str
