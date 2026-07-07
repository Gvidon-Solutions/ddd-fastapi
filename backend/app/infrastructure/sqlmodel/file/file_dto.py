"""File SQLModel DTO."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.file import (
    File,
    FileKind,
    FileLocation,
    FileStatus,
)
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


class FileDTO(SQLModel, table=True):
    """Persisted file metadata."""

    __tablename__ = "file"

    file_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=255)
    kind: str = Field(max_length=32)
    location_uri: str = Field(max_length=4096)
    file_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    status: str = Field(max_length=32, index=True)
    delete_requested_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    delete_attempts: int = Field(default=0)
    last_delete_error: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    def to_entity(self) -> File:
        """Convert this DTO to a domain file."""
        return File(
            file_id=self.file_id,
            name=self.name,
            kind=FileKind(self.kind),
            location=FileLocation(
                uri=self.location_uri,
            ),
            metadata=self.file_metadata,
            status=FileStatus(self.status),
            delete_requested_at=ensure_datetime_utc(self.delete_requested_at)
            if self.delete_requested_at is not None
            else None,
            delete_attempts=self.delete_attempts,
            last_delete_error=self.last_delete_error,
            created_at=ensure_datetime_utc(self.created_at),
        )

    @staticmethod
    def from_entity(file: File) -> FileDTO:
        """Build a DTO from a domain file."""
        return FileDTO(
            file_id=file.file_id,
            name=file.name,
            kind=file.kind.value,
            location_uri=file.location.uri,
            file_metadata=file.metadata,
            status=file.status.value,
            delete_requested_at=file.delete_requested_at,
            delete_attempts=file.delete_attempts,
            last_delete_error=file.last_delete_error,
            created_at=file.created_at,
        )
