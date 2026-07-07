"""Define the File entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.file.value_objects import FileId, FileKind, FileLocation, FileStatus


@dataclass(frozen=True)
class File:
    """Represent stored file metadata."""

    file_id: FileId
    name: str
    kind: FileKind
    location: FileLocation
    metadata: dict
    status: FileStatus
    delete_requested_at: datetime | None
    delete_attempts: int
    last_delete_error: str | None
    created_at: datetime
